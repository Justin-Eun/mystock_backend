import asyncio
import httpx
import json

async def test_search():
    # Naver Finance Autocomplete
    url = "https://ac.finance.naver.com/ac"
    
    # Need to check if query needs to be explicitly encoded or if httpx handles it
    # Naver often expects UTF-8 if q_enc=utf-8
    
    params = {
        "q": "삼성전자",
        "q_enc": "utf-8",
        "st": "111",
        "r_lt": "111"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.naver.com/"
    }
    
    print(f"Testing Naver AC for: 삼성전자")
    async with httpx.AsyncClient() as client:
        res = await client.get(url, params=params, headers=headers)
        print(f"Status: {res.status_code}")
        print(res.text[:500])
        
        try:
            data = res.json()
            # Naver AC structure is typically:
            # {"query":["..."],"items":[[[["005930","삼성전자","..."]]]]}
            items = data.get("items", [])
            if items and len(items) > 0:
                first_group = items[0]
                for item in first_group:
                    code = item[0]
                    name = item[1]
                    print(f" - Code: {code} | Name: {name}")
        except Exception as e:
            print(f"Error parsing: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
