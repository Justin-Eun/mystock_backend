import requests
try:
    res = requests.get("http://localhost:8001/api/stock/005930/price?timeframe=day")
    data = res.json()
    print(f"Items returned: {len(data)}")
    if len(data) > 0:
        print(f"First date: {data[0]['date']}")
        print(f"Last date: {data[-1]['date']}")
except Exception as e:
    print(f"Error: {e}")
