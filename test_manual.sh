#!/bin/bash

set -e

export WEBHOOK_SECRET="testsecret"

echo "=== Testing Webhook API ==="

echo "1. Computing signature for test message..."
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'

SIGNATURE=$(python3 << EOF
import hmac, hashlib
secret = "$WEBHOOK_SECRET"
body = '''$BODY'''
print(hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest())
EOF
)

echo "Signature: $SIGNATURE"

echo ""
echo "2. Testing health endpoints..."
curl -sf http://localhost:8000/health/live && echo " ✓ Liveness OK"
curl -sf http://localhost:8000/health/ready && echo " ✓ Readiness OK"

echo ""
echo "3. Testing invalid signature (expect 401)..."
curl -s -o /dev/null -w "Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid" \
  -d "$BODY" \
  http://localhost:8000/webhook

echo ""
echo "4. Testing valid webhook request (expect 200)..."
curl -s -w "Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY" \
  http://localhost:8000/webhook

echo ""
echo "5. Testing duplicate request (expect 200, idempotent)..."
curl -s -w "Status: %{http_code}\n" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY" \
  http://localhost:8000/webhook

echo ""
echo "6. Listing messages..."
curl -s "http://localhost:8000/messages" | python3 -m json.tool

echo ""
echo "7. Getting stats..."
curl -s "http://localhost:8000/stats" | python3 -m json.tool

echo ""
echo "8. Checking metrics..."
curl -s "http://localhost:8000/metrics" | head -20

echo "" 
echo "=== All tests completed ==="
