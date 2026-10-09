import urllib.request
import json

data = json.dumps({
    "jsonrpc": "2.0",
    "method": "call",
    "params": {},
    "id": 1
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8069/eh_monthly_disbursement/dashboard_data',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    response = urllib.request.urlopen(req)
    print(response.read().decode('utf-8'))
except Exception as e:
    print(e)
