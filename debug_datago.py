import os
import requests
import json
from dotenv import load_dotenv
from urllib.parse import unquote

load_dotenv()

# The key in .env might be already encoded. 
# Usually requests library handles encoding if passed as params, 
# but for serviceKey in Korean public APIs, it's often tricky.
# We try both encoded and decoded versions if one fails.

API_KEY = os.getenv("DATA_GO_KR_API_KEY")
DECODED_KEY = unquote(API_KEY)

URL = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"

def test_api(key_to_use, desc):
    print(f"\n--- Testing with {desc} ---")
    params = {
        "serviceKey": key_to_use,
        "numOfRows": 10,
        "pageNo": 1,
        "resultType": "json",
        "itmsNm": "삼성전자" # Search for Samsung Electronics
    }
    
    try:
        # Note: requests automatically encodes params. 
        # If the key is ALREADY encoded, passing it in params might double-encode it.
        # So for the 'serviceKey', we might need to append it manually or use the decoded one.
        
        # Test 1: Standard params (Requests will encode)
        res = requests.get(URL, params=params)
        print(f"Status: {res.status_code}")
        print(f"URL: {res.url}")
        print(f"Content: {res.text[:300]}")
        
        if "<resultCode>00</resultCode>" in res.text or '"resultCode":"00"' in res.text:
             print("SUCCESS!")
             return True
        else:
             print("FAILED response check.")
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    print(f"Loaded Key: {API_KEY[:10]}...")
    
    # Usually, we need the DECODED key because requests will encode it.
    if test_api(DECODED_KEY, "Decoded Key"):
        pass
    else:
        # Sometimes we just pass the encoded key directly in the URL string to be safe
        print("\n--- Testing Manual URL Construction ---")
        full_url = f"{URL}?serviceKey={API_KEY}&numOfRows=10&pageNo=1&resultType=json&itmsNm=삼성전자"
        res = requests.get(full_url)
        print(f"Status: {res.status_code}")
        print(f"Content: {res.text[:300]}")
