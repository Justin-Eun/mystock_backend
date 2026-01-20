import requests
import json

BASE_URL = "http://localhost:8001"

def test_endpoints():
    print("Testing Endpoints...")
    
    # 1. Favorites
    try:
        print("\n--- GET /api/favorites ---")
        res = requests.get(f"{BASE_URL}/api/favorites", timeout=5)
        print(f"Status: {res.status_code}")
        print(f"Data: {res.json()}")
    except Exception as e:
        print(f"FAIL: {e}")

    # 2. Stock Price (Samsung Electronics)
    try:
        print("\n--- GET /api/stock/005930/price ---")
        res = requests.get(f"{BASE_URL}/api/stock/005930/price", timeout=10)
        print(f"Status: {res.status_code}")
        # Print only first item to save space
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            print(f"Data Sample: {data[0]}")
        else:
            print(f"Data: {data}")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    test_endpoints()
