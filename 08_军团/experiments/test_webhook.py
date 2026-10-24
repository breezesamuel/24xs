import urllib.request
import json

url = "https://geo-audit-24xs.vercel.app/api/webhook/moltspay"
data = json.dumps({
    "type": "payment.succeeded",
    "data": {
        "id": "test_123",
        "amount": 60000,
        "customer_email": "test@example.com"
    }
}).encode()

req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "X-MoltsPay-Signature": "test"
}, method="POST")

try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"Status: {r.status}")
        print(f"Response: {r.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"Error: {e}")