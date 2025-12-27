# Webhook API - Lyftr AI Backend Assignment

A production-style FastAPI service for ingesting WhatsApp-like messages with HMAC signature validation, health probes, pagination, analytics, and Prometheus metrics.

## Features

- **Idempotent webhook ingestion** with HMAC-SHA256 signature validation
- **Pagination and filtering** for message retrieval
- **Analytics endpoint** with sender statistics
- **Health probes** for liveness and readiness checks
- **Prometheus metrics** for observability
- **Structured JSON logging** for all requests
- **SQLite database** with Docker volume persistence
- **12-factor configuration** via environment variables

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience)

### Running the Service

1. Set the required environment variable:

```bash
export WEBHOOK_SECRET="testsecret"
```

2. Start the service:

```bash
make up
```

Or without Make:

```bash
docker compose up -d --build
```

3. Check service health:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

### Stopping the Service

```bash
make down
```

Or:

```bash
docker compose down -v
```

## API Endpoints

### POST /webhook

Ingest WhatsApp-like messages with HMAC signature validation.

**Headers:**
- `Content-Type: application/json`
- `X-Signature: demo-signature (without this we get 401 error)`

**Body:**
```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200`: Success (message created or duplicate)
- `401`: Invalid or missing signature
- `422`: Validation error

### GET /messages

List stored messages with pagination and filtering.

**Query Parameters:**
- `limit` (optional, int, default=50, min=1, max=100): Number of results
- `offset` (optional, int, default=0, min=0): Skip N results
- `from` (optional, string): Filter by sender phone number (exact match)
- `since` (optional, ISO-8601 string): Filter messages after timestamp
- `q` (optional, string): Search text content (case-insensitive)

**Example:**
```bash
curl "http://localhost:8000/messages?limit=10&offset=0&from=%2B919876543210"
```

**Response:**
```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### GET /stats

Get message analytics.

**Response:**
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    { "from": "+919876543210", "count": 50 },
    { "from": "+911234567890", "count": 30 }
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

### GET /health/live

Liveness probe - always returns 200 when the app is running.

### GET /health/ready

Readiness probe - returns 200 when:
- Database is reachable
- WEBHOOK_SECRET is configured

Returns 503 if not ready.

### GET /metrics

Prometheus-style metrics endpoint.

**Metrics:**
- `http_requests_total{path, status}`: Total HTTP requests by path and status
- `webhook_requests_total{result}`: Webhook outcomes (created, duplicate, invalid_signature, validation_error)
- `request_latency_ms_bucket{le}`: Request latency histogram

## Design Decisions

### HMAC Verification

The service implements HMAC-SHA256 signature verification to ensure message authenticity:

1. Server reads `WEBHOOK_SECRET` from environment variable
2. For each request, compute: `HMAC-SHA256(secret, raw_body_bytes)`
3. Compares computed signature with `X-Signature` header using constant-time comparison
4. Rejects requests with invalid/missing signatures with 401 status
5. No database operations occur for invalid signatures

### Idempotency

Idempotency is enforced at two levels:

1. **Database level**: `message_id` is the PRIMARY KEY, preventing duplicate inserts
2. **Application level**: SQLite `IntegrityError` is caught and treated as a duplicate, returning 200

This ensures exactly-once semantics even with retries.

### Pagination Contract

The `/messages` endpoint uses offset-based pagination:

- **Deterministic ordering**: `ORDER BY ts ASC, message_id ASC`
- **Total count**: Always reflects total matching rows (ignoring limit/offset)
- **Filter preservation**: Filters apply before pagination
- **Bounds checking**: Pydantic validates min/max values

Example: If 100 messages match filters, `total=100` regardless of `limit` and `offset`.

### Stats Implementation

The `/stats` endpoint uses SQL aggregations for efficiency:

- `total_messages`: Simple COUNT(*)
- `senders_count`: COUNT(DISTINCT from_msisdn)
- `messages_per_sender`: GROUP BY with ORDER BY count DESC LIMIT 10
- `first_message_ts` / `last_message_ts`: MIN(ts) and MAX(ts)

Returns `null` for timestamps when no messages exist.

### Metrics Design

Prometheus metrics use counter and histogram types:

- **Counters** increment on each event with labels for categorisation
- **Histograms** track latency distribution using predefined buckets (100ms, 500ms, +Inf)
- Thread-safe implementation using locks for concurrent request handling
- Metrics survive for the process lifetime (in-memory)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:////data/app.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `WEBHOOK_SECRET` | Yes | - | HMAC secret for signature validation |

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes, middleware
│   ├── models.py            # Pydantic models
│   ├── storage.py           # Database operations
│   ├── logging_utils.py     # JSON logger setup
│   ├── metrics.py           # Prometheus metrics collector
│   └── config.py            # Environment configuration
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures
│   ├── test_webhook.py      # Webhook endpoint tests
│   ├── test_messages.py     # Messages endpoint tests
│   ├── test_stats.py        # Stats endpoint tests
│   └── test_health.py       # Health probe tests
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Service configuration
├── Makefile                 # Convenience commands
├── pyproject.toml           # Poetry dependencies
├── requirements.txt         # Pip dependencies
└── README.md                # This file
```

## Testing

Run tests inside the Docker container:

```bash
make test
```

Or manually:

```bash
docker compose exec api pytest tests/ -v
```

## Logs

View structured JSON logs:

```bash
make logs
```

Or:

```bash
docker compose logs -f api
```

Each log line includes:
- `ts`: ISO-8601 timestamp
- `level`: Log level
- `request_id`: Unique request identifier
- `method`: HTTP method
- `path`: Request path
- `status`: HTTP status code
- `latency_ms`: Request duration

For webhook requests, additional fields:
- `message_id`: Message identifier
- `dup`: Boolean indicating duplicate
- `result`: Outcome (created, duplicate, invalid_signature, validation_error)

## Example Usage

### Sending a valid webhook request

```bash
# Compute signature (example using Python)
python3 << EOF
import hmac, hashlib, json

secret = "testsecret"
body = json.dumps({
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello"
})

signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
print(f"Signature: {signature}")
print(f"Body: {body}")
EOF

# Send request with computed signature
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <computed_signature>" \
  -d '<body>'
```

### Querying messages

```bash
# List all messages
curl "http://localhost:8000/messages"

# Filter by sender
curl "http://localhost:8000/messages?from=%2B919876543210"

# Search text content
curl "http://localhost:8000/messages?q=Hello"

# Pagination
curl "http://localhost:8000/messages?limit=10&offset=20"

# Multiple filters
curl "http://localhost:8000/messages?from=%2B919876543210&since=2025-01-15T10:00:00Z&q=Hello"
```

### Viewing stats

```bash
curl "http://localhost:8000/stats" | jq .
```

### Checking metrics

```bash
curl "http://localhost:8000/metrics"
```

## Setup Used

VSCode + Claude Code + FastAPI Documentation

## License

MIT

## Submission

For Lyftr AI Backend Assignment - Containerized Webhook API
