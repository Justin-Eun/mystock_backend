import requests
import json

BASE_URL = "http://localhost:8001"

def test_endpoints():
    print("Testing Endpoints...")

    # 1. Analyze (This is the suspected hanging point)
    try:
        print("\n--- POST /api/analyze ---")
        payload = {"stock_code": "005930", "stock_name": "Samsung"}
        res = requests.post(f"{BASE_URL}/api/analyze", json=payload, timeout=10)
        print(f"Status: {res.status_code}")
        print(f"Data: {res.json()}")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    test_endpoints()
