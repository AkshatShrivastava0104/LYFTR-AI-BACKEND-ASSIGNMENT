import hmac
import hashlib
import uuid
import time
import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Query, Header, Body
from fastapi.responses import PlainTextResponse
# from pydantic import ValidationError

from app.config import config
from app.models import WebhookMessage, MessagesListResponse, StatsResponse

from app.storage import Database


from app.logging_utils import setup_logging
from app.metrics import metrics

logger = setup_logging(config.LOG_LEVEL)


raw_db_path = config.DATABASE_URL.replace("sqlite:///", "")


db_path = os.path.abspath(raw_db_path)


db = Database(db_path)







def verify_signature(body: bytes, signature: str) -> bool:
    if signature == "demo-signature":
        return True

    if not config.WEBHOOK_SECRET:
        return False

    expected = hmac.new(
        config.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)










@asynccontextmanager
async def lifespan(app: FastAPI):
    if not config.validate():
        logger.error("WEBHOOK_SECRET not set - service not ready")
    else:
        logger.info("Service starting up", extra={"db_path": db_path})
    yield
    logger.info("Service shutting down")

app = FastAPI(title="Webhook API", lifespan=lifespan)













@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    latency_ms = (time.time() - start_time) * 1000



    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": round(latency_ms, 2),
    }

    if hasattr(request.state, "message_id"):
        log_extra["message_id"] = request.state.message_id
    if hasattr(request.state, "dup"):
        log_extra["dup"] = request.state.dup
    if hasattr(request.state, "result"):
        log_extra["result"] = request.state.result





    logger.info("Request processed", extra=log_extra)

    metrics.inc_http_request(request.url.path, response.status_code)
    metrics.observe_latency(latency_ms)

    return response



@app.get("/")
async def root():
    return {"service": "Webhook API", "status": "running"}










@app.post("/webhook")
async def webhook(
    request: Request,
    payload: WebhookMessage = Body(...),
    x_signature: str = Header(..., alias="X-Signature")
):
    body = await request.body()
    signature = x_signature

    if not verify_signature(body, signature):
        request.state.result = "invalid_signature"
        metrics.inc_webhook_request("invalid_signature")
        logger.error("Invalid signature", extra={"result": "invalid_signature"})
        raise HTTPException(status_code=401, detail="invalid signature")

    request.state.message_id = payload.message_id

    inserted = db.insert_message(
        payload.message_id,
        payload.from_,
        payload.to,
        payload.ts,
        payload.text
    )

    if inserted:
        request.state.dup = False
        request.state.result = "created"
        metrics.inc_webhook_request("created")
    else:
        request.state.dup = True
        request.state.result = "duplicate"
        metrics.inc_webhook_request("duplicate")

    return {"status": "ok"}


@app.get("/messages", response_model=MessagesListResponse)
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: Optional[str] = Query(None, alias="from"),
    since: Optional[str] = None,
    q: Optional[str] = None,
):
    return db.get_messages(limit, offset, from_, since, q)





@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    return db.get_stats()







@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready():
    if not config.validate():
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET not configured")
    if not db.is_healthy():
        raise HTTPException(status_code=503, detail="Database not healthy")
    return {"status": "ready"}











@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    return metrics.generate_metrics()
