import os
import hmac
import hashlib
import tempfile
import pytest
from fastapi.testclient import TestClient

os.environ["WEBHOOK_SECRET"] = "testsecret"
os.environ["DATABASE_URL"] = "sqlite:////tmp/test_app.db"

from app.main import app, db

@pytest.fixture
def client():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from app.storage import Database
    test_db = Database(db_path)

    with TestClient(app) as test_client:
        yield test_client

    os.unlink(db_path)

def compute_signature(body: str, secret: str = "testsecret") -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
