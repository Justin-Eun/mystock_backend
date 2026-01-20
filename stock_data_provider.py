import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import httpx
import os
import requests
from urllib.parse import unquote

# DEBUG PRINT TO CONFIRM LOAD
print("!!! LOADING STOCK_DATA_PROVIDER.PY - HYBRID (PUBLIC DATA + FDR) !!!")

KRX_CACHE = {
    "name_map": {}, # Name -> Code
    "code_map": {}, # Code -> Name
    "loaded": False
}

def load_krx_data():
    if KRX_CACHE["loaded"]:
        return

    print("[DEBUG] Loading KRX Master List...")
    try:
        url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
        # Explicit encoding for Korean Windows site
        dfs = pd.read_html(url, header=0, encoding='euc-kr') 
        df = dfs[0]
        
        # Clean up
        df = df[['회사명', '종목코드']]
        df = df.rename(columns={'회사명': 'name', '종목코드': 'code'})
        df['code'] = df['code'].astype(str).str.zfill(6)
        
        for _, row in df.iterrows():
            KRX_CACHE["name_map"][row['name']] = row['code']
            KRX_CACHE["code_map"][row['code']] = row['name']
            
        KRX_CACHE["loaded"] = True
        print(f"[DEBUG] Loaded {len(df)} Korean stocks.")
    except Exception as e:
        print(f"[ERROR] Failed to load KRX data: {e}")

async def search_stock(query: str):
    print(f"[DEBUG] Searching stock for: {query}")
    
    # Ensure data is loaded (blocking call ok for first time/cache)
    if not KRX_CACHE["loaded"]:
        load_krx_data()
        
    results = []
    query = query.strip()
    
    # 1. Search in Local KRX Cache (Exact & Contains)
    for name, code in KRX_CACHE["name_map"].items():
        if query.lower() in name.lower():
            # Exact match prioritization
            score = 10 if query == name else 5
            results.append({
                "symbol": f"{code}",  # Keep simplified for FDR
                "code": code,
                "name": name,
                "type": "Equity",
                "exch": "KRX",
                "score": score
            })
            
    # 2. Search Yahoo Finance Global (for US/Global stocks)
    yahoo_url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": 6,
        "newsCount": 0,
        "enableFuzzyQuery": "false",
        "quotesQueryId": "tss_match_phrase_query"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(yahoo_url, params=params, headers=headers)
            if res.status_code == 200:
                y_data = res.json()
                quotes = y_data.get("quotes", [])
                
                for q in quotes:
                    symbol = q.get("symbol", "")
                    shortname = q.get("shortname") or q.get("longname") or symbol
                    exch = q.get("exchange", "Unknown")
                    quoteType = q.get("quoteType", "")
                    
                    # Filter out useless types
                    if quoteType not in ["EQUITY", "ETF", "MUTUALFUND"]:
                        continue
                        
                    # Avoid duplicates if we already found them via KRX (check by code)
                    if any(r["code"] == symbol for r in results):
                        continue
                        
                    results.append({
                        "symbol": symbol, 
                        "code": symbol,   
                        "name": shortname,
                        "type": quoteType,
                        "exch": exch,
                        "score": 8 if symbol.lower() == query.lower() else 3
                    })
    except Exception as e:
        print(f"[ERROR] Yahoo Search failed: {e}")
            
    # Sort by relevance
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Cap results
    if len(results) > 15:
        results = results[:15]
    
    return results

def fetch_public_data(code: str, start_date: str, end_date: str):
    """
    Fetch from Public Data Portal (data.go.kr)
    """
    api_key = os.getenv("DATA_GO_KR_API_KEY")
    if not api_key:
        print("[DEBUG] No Public Data API Key found.")
        return None

    # Handle URL encoding of key if needed
    decoded_key = unquote(api_key) 
    
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    
    # Dates for API are typically YYYYMMDD
    # Input start_date is YYYY-MM-DD
    s_date = start_date.replace("-", "") if start_date else ""
    e_date = end_date.replace("-", "") if end_date else ""
    
    # Basic Params
    params = {
        "serviceKey": decoded_key,
        "numOfRows": 1000, # Max rows to get a good chunk
        "pageNo": 1,
        "resultType": "json",
        "likeSrtnCd": code # Search by Short Code (e.g. 005930)
    }
    
    if s_date: params["beginBasDt"] = s_date
    if e_date: params["endBasDt"] = e_date

    print(f"[DEBUG] Public API fetching for {code}...")
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            print(f"[ERROR] Public API Status: {res.status_code}")
            return None
            
        data = res.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        
        if not items:
            print("[DEBUG] Public API returned no items.")
            return None
            
        # Parse items
        parsed_data = []
        for item in items:
            # item fields: basDt (20240120), clpr (74000)
            d_str = item.get("basDt")
            close_val = item.get("clpr")
            
            if d_str and close_val:
                fmt_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                parsed_data.append({
                    "date": fmt_date,
                    "close": int(close_val)
                })
        
        # Sort by date ascending
        parsed_data.sort(key=lambda x: x["date"])
        print(f"[DEBUG] Public API success. {len(parsed_data)} points.")
        return parsed_data
        
    except Exception as e:
        print(f"[ERROR] Public API fetch exception: {e}")
        return None

async def get_stock_price(code: str, timeframe: str = "day", start_date: str = None, end_date: str = None):
    print(f"[DEBUG] get_stock_price called via HYBRID PROVIDER. Code: {code}")
    
    if not KRX_CACHE["loaded"]:
        load_krx_data()
        
    stock_name = KRX_CACHE["code_map"].get(code, code)
    is_krx_code = code.isdigit() and len(code) == 6
    
    data = []
    
    # --- STRATEGY 1: Public Data Portal (Only for Korean Stocks) ---
    if is_krx_code:
        # Default dates if missing
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Run in executor to avoid blocking async loop since requests is sync
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: fetch_public_data(code, start_date, end_date))
        
        if data:
            print(f"[DEBUG] Data provided by Public Data Portal.")
            return {"name": stock_name, "data": data}
        else:
            print(f"[WARN] Public Data Portal failed/empty. Falling back to FinanceDataReader.")
            data = [] # Reset for fallback

    # --- STRATEGY 2: FinanceDataReader (Fallback for KRX, Primary for US) ---
    try:
        # FDR requires dates in YYYY-MM-DD
        s_d = start_date if start_date else "2023-01-01"
        e_d = end_date if end_date else datetime.now().strftime("%Y-%m-%d")
        
        loop = asyncio.get_event_loop()
        
        # Determine symbol for FDR
        # For KRX: '005930' (FDR handles suffixes auto for Korea if just digits?) 
        # Actually FDR works best with '005930' (Naver) or 'KRX:005930'
        # For US: 'AAPL', 'RDW'
        
        fdr_symbol = code
        # No change needed usually for FDR if code is standard
        
        def fetch_fdr(sym, start, end):
            # FDR returns a DataFrame
            df = fdr.DataReader(sym, start, end)
            return df
            
        df = await loop.run_in_executor(None, lambda: fetch_fdr(fdr_symbol, s_d, e_d))
        
        if not df.empty:
            # reset_index moves 'Date' (or 'index') to a column
            df = df.reset_index()
            
            # Identify the date column and close column
            date_col = 'Date' if 'Date' in df.columns else ('index' if 'index' in df.columns else df.columns[0])
            close_col = 'Close'
            
            for index, row in df.iterrows():
                try:
                    d_val = row[date_col]
                    
                    # Convert Timestamp to string
                    d_str = ""
                    if isinstance(d_val, (pd.Timestamp, datetime)):
                        d_str = d_val.strftime("%Y-%m-%d")
                    else:
                        d_str = str(d_val)[:10] # Handle string dates if any
                    
                    close_val = row[close_col]
                    
                    # Formatting check
                    final_close = 0
                    if hasattr(close_val, 'item'): close_val = close_val.item() # Handle numpy types
                    
                    if pd.isna(close_val): continue
                    
                    if isinstance(close_val, float):
                         final_close = int(close_val) if close_val > 5000 else round(close_val, 2)
                    else:
                         final_close = int(close_val)
                    
                    data.append({
                        "date": d_str,
                        "close": final_close
                    })
                except Exception as e:
                    # print(f"[DEBUG] Row parsing error: {e}")
                    continue
                    
            print(f"[DEBUG] FDR Success. {len(data)} points.")
            
            return {
                "name": stock_name, 
                "data": data
            }
            
    except Exception as e:
        print(f"[ERROR] FDR failed: {e}")

    return {
        "name": stock_name + " (No Data)",
        "data": []
    }

async def get_financials(code: str):
    # Mock for now
    return {
        "revenue": "100B",
        "operating_profit": "10B",
        "net_income": "8B",
        "per": 12.5,
        "pbr": 1.2
    }
