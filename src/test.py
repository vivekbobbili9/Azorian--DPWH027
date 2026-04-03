import requests

r = requests.post("http://127.0.0.1:8000/simulate")
print("Status:", r.status_code)
print("Raw response:", r.text)

# Also test health
r2 = requests.get("http://127.0.0.1:8000/health")
print("Health status:", r2.status_code)
print("Health response:", r2.text)