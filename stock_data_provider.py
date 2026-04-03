import logging
import asyncio
import threading
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import re

# Optional Selenium imports (handled gracefully if missing)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import httpx
import os
import requests
from urllib.parse import unquote

import logging

# Configure Logging (Writes to stderr by default, safe for MCP)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# DEBUG PRINT TO CONFIRM LOAD
logger.info("!!! LOADING STOCK_DATA_PROVIDER.PY - HYBRID (PUBLIC DATA + FDR) !!!")

KRX_CACHE = {
    "name_map": {}, # Name -> Code
    "code_map": {}, # Code -> Name
    "loaded": False
}

def load_krx_data():
    if KRX_CACHE["loaded"]:
        return

    logger.info("[DEBUG] Loading KRX Master List...")
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
        logger.info(f"[DEBUG] Loaded {len(df)} Korean stocks.")
    except Exception as e:
        logger.info(f"[ERROR] Failed to load KRX data: {e}")

async def search_stock(query: str):
    logger.info(f"[DEBUG] Searching stock for: {query}")
    
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
        logger.info(f"[ERROR] Yahoo Search failed: {e}")
            
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
        logger.info("[DEBUG] No Public Data API Key found.")
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

    logger.info(f"[DEBUG] Public API fetching for {code}...")
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            logger.info(f"[ERROR] Public API Status: {res.status_code}")
            return None
            
        data = res.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        
        if not items:
            logger.info("[DEBUG] Public API returned no items.")
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
        logger.info(f"[DEBUG] Public API success. {len(parsed_data)} points.")
        return parsed_data
        
    except Exception as e:
        logger.info(f"[ERROR] Public API fetch exception: {e}")
        return None

async def get_stock_price(code: str, timeframe: str = "day", start_date: str = None, end_date: str = None):
    logger.info(f"[DEBUG] get_stock_price called via HYBRID PROVIDER. Code: {code}")
    
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
            logger.info(f"[DEBUG] Data provided by Public Data Portal.")
            return {"name": stock_name, "data": data}
        else:
            logger.info(f"[WARN] Public Data Portal failed/empty. Falling back to FinanceDataReader.")
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
                    
            logger.info(f"[DEBUG] FDR Success. {len(data)} points.")
            
            return {
                "name": stock_name, 
                "data": data
            }
            
    except Exception as e:
        logger.info(f"[ERROR] FDR failed: {e}")

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

async def get_global_market_indices():
    """
    Fetch global market indices for the dashboard.
    """
    indices = {
        "US_10Y": "^TNX",
        "DXY": "DX-Y.NYB",
        "USD_KRW": "KRW=X",
        "VIX": "^VIX",
        "BTC": "BTC-USD",
        "ES_F": "ES=F",
        "NQ_F": "NQ=F",
        "WTI": "CL=F",
        "KR_FUTURES": "INVESTING_KR",  # Korean night futures from Investing.com
        "DXI": "MACROMICRO_DXI",  # DRAM Stock Index from MacroMicro
        "FearGreed": "MOCK_FG",  # Special handle
        "KoreanCDS": "MOCK_CDS"  # Special handle
    }

    results = {}
    
    # We will fetch only the last 2 days to calculate change
    # loop = asyncio.get_event_loop()  <-- REMOVED: Do not use global loop

    # Lock for driver creation to avoid race conditions with webdriver_manager
    _driver_lock = threading.Lock()

    def _get_selenium_driver():
        """Helper to create a headless chrome driver safely"""
        if not SELENIUM_AVAILABLE:
            return None
        
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            # ... options ...
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--window-size=1200,800")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Simple install - webdriver_manager handles caching
            # Lock only the installation/cache check part
            with _driver_lock:
                service = Service(ChromeDriverManager().install())
                
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(15)
            return driver
        except Exception as e:
            logger.error(f"Failed to create Selenium driver: {e}")
            return None

    
    def fetch_index(key, symbol):
        # MOCK DATA FOR MISSING APIs
        if key == "FearGreed":
            # Real API harder to find, returning static/random for MVP
            return key, {
                "value": 45, 
                "prev": 48, 
                "change": -3, 
                "pct_change": -6.25
            }
        if key == "KoreanCDS":
            return key, {
                "value": 32.5, 
                "prev": 32.0, 
                "change": 0.5, 
                "pct_change": 1.56
            }
        if key == "DXI":
            # DRAM Stock Index from MacroMicro (Selenium required)
            driver = None
            try:
                driver = _get_selenium_driver()
                if not driver:
                    raise Exception("Selenium driver unavailable")

                import time as _time
                
                driver.get("https://en.macromicro.me/series/2793/semiconductor-dram-stock-index")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".mm-cc-chart-stats-title, [class*=stat], span.val"))
                )
                _time.sleep(1.0)
                
                # Extract DXI value using precise CSS classes
                dxi_data = driver.execute_script("""
                    var result = {};
                    
                    var statVal = document.querySelector('.stat-val .val, .stat-val, span.val');
                    if (statVal) result.current = parseFloat(statVal.textContent.trim().replace(/,/g, ''));
                    
                    var prevVal = document.querySelector('.prev-val .val, .prev-val');
                    if (prevVal) result.prev = parseFloat(prevVal.textContent.trim().replace(/,/g, ''));
                    
                    var deltaVal = document.querySelector('.delta-val .val, .delta-val');
                    if (deltaVal) result.delta = parseFloat(deltaVal.textContent.trim().replace(/,/g, ''));
                    
                    return result;
                """)
                
                if dxi_data and dxi_data.get('current'):
                    val = dxi_data['current']
                    prev = dxi_data.get('prev', val)
                    change = dxi_data.get('delta', val - prev)
                    pct_change = (change / prev) * 100 if prev != 0 else 0
                    
                    return key, {
                        "value": round(float(val), 2),
                        "prev": round(float(prev), 2),
                        "change": round(float(change), 2),
                        "pct_change": round(float(pct_change), 2)
                    }
            except Exception as dxi_err:
                logger.info(f"[ERROR] Failed to fetch DXI: {dxi_err}")
                return key, None
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass

        if key == "KR_FUTURES":
            # Scrape from kr.investing.com
            driver = None
            try:
                driver = _get_selenium_driver()
                if not driver:
                    raise Exception("Selenium driver unavailable")

                import time as _time
                
                url = "https://kr.investing.com/indices/korea-200-futures"
                driver.get(url)
                
                # Wait for the price element to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="instrument-price-last"]'))
                )
                _time.sleep(1)
                
                # Extract data via JavaScript using data-test attributes
                data = driver.execute_script("""
                    var result = {};
                    var priceEl = document.querySelector('[data-test="instrument-price-last"]');
                    var changeEl = document.querySelector('[data-test="instrument-price-change"]');
                    var pctEl = document.querySelector('[data-test="instrument-price-change-percent"]');
                    if (priceEl) result.price = priceEl.textContent.trim();
                    if (changeEl) result.change = changeEl.textContent.trim();
                    if (pctEl) result.pct = pctEl.textContent.trim();
                    return result;
                """)
                
                if data and data.get('price'):
                    val = float(data['price'].replace(',', ''))
                    change_str = data.get('change', '0').replace('+', '').replace(',', '')
                    change = float(change_str)
                    pct_str = data.get('pct', '0%').replace('(', '').replace(')', '').replace('%', '').replace('+', '')
                    pct_change = float(pct_str)
                    prev = val - change
                    
                    return key, {
                        "value": round(val, 2),
                        "prev": round(prev, 2),
                        "change": round(change, 2),
                        "pct_change": round(pct_change, 2)
                    }
            except Exception as kr_err:
                logger.info(f"[ERROR] Failed to fetch Korean night futures: {kr_err}")
                return key, None
            finally:
                if driver: 
                    try:
                        driver.quit()
                    except:
                        pass

        try:
            # Special handling for BTC - try direct Yahoo Finance API first
            if key == "BTC":
                try:
                    import yfinance as yf
                    btc = yf.Ticker("BTC-USD")
                    hist = btc.history(period="5d")
                    if not hist.empty and len(hist) >= 2:
                        val = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2]
                        if not pd.isna(val) and not pd.isna(prev):
                            change = val - prev
                            pct_change = (change / prev) * 100 if prev != 0 else 0
                            return key, {
                                "value": float(val),
                                "prev": float(prev),
                                "change": float(change),
                                "pct_change": float(pct_change)
                            }
                except Exception as yf_err:
                    logger.info(f"[WARN] yfinance failed for BTC, trying FDR: {yf_err}")
            
            # Fetch last 5 distinct trading days to be safe
            df = fdr.DataReader(symbol, (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"))
            if df.empty:
                return key, None
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else last_row
            
            val = last_row['Close']
            prev = prev_row['Close']

            # Check for NaN immediately
            if pd.isna(val) or pd.isna(prev):
                return key, None
            
            # Formatting
            if key == "US_10Y":
                val = round(float(val), 2)  # Format to 2 decimal places
                prev = round(float(prev), 2)
            
            change = val - prev
            pct_change = (change / prev) * 100 if prev != 0 else 0
            
            # Final check for calculated NaNs (e.g. if prev was 0 or something weird)
            if pd.isna(change) or pd.isna(pct_change):
                return key, None
            
            return key, {
                "value": float(val), # Ensure native float
                "prev": float(prev),
                "change": float(change),
                "pct_change": float(pct_change)
            }
        except Exception as e:
            logger.info(f"[ERROR] Failed to fetch {key} ({symbol}): {e}")
            return key, None

    # Use running loop to ensure compatibility with Uvicorn
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
        
    async def fetch_with_timeout(key, symbol):
        # Set individual timeouts
        # DXI and KR_FUTURES involve Selenium, so give them more time but cap them
        # Set individual timeouts
        # DXI and KR_FUTURES involve Selenium, so give them more time
        # Increased to 40s based on user logs showing 15s is insufficient
        timeout = 40 if key in ["DXI", "KR_FUTURES"] else 15
        try:
            # wait_for works on the Future returned by run_in_executor
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: fetch_index(key, symbol)), 
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[WARN] Timeout fetching {key} after {timeout}s")
            return key, None
        except Exception as e:
            logger.error(f"[ERROR] Exception fetching {key}: {e}")
            return key, None

    # Create tasks with individual timeouts
    tasks = [fetch_with_timeout(k, s) for k, s in indices.items()]
    
    # Run all tasks concurrently
    # Since each task handles its own timeout, we don't strictly need a timeout here
    fetched = await asyncio.gather(*tasks, return_exceptions=True)
    
    for item in fetched:
        if isinstance(item, Exception):
            logger.error(f"[ERROR] Unhandled task exception: {item}")
            continue
        if not item: continue
        
        # item is expected to be (key, data) or None
        if isinstance(item, tuple) and len(item) == 2:
            k, v = item
            if v is not None:
                results[k] = v
            
    return results

