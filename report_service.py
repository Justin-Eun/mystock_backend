import requests
from bs4 import BeautifulSoup
import logging
import asyncio
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CACHE = {
    "data": [],
    "last_fetched": 0
}

def analyze_sentiment(title: str):
    """
    Determine sentiment based on keywords in the title.
    """
    positive_keywords = [
        "성장", "최대", "개선", "상향", "호조", "기대", "매수", "확대",
        "상회", "부합", "증설", "서프라이즈", "견조", "도약", "유망", "저평가", "강세", "회복", "반등"
    ]
    negative_keywords = [
        "하향", "우려", "축소", "감소", "부진", "적자", "둔화", "불확실",
        "하회", "아쉽", "부담", "리스크", "약세", "쇼크", "지연"
    ]

    score = 0
    for kw in positive_keywords:
        if kw in title:
            score += 1
            
    for kw in negative_keywords:
        if kw in title:
            score -= 1
            
    if score > 0:
        return "Positive"
    elif score < 0:
        return "Negative"
    else:
        return "Neutral"

def fetch_hankyung_reports(start_date: str = None, end_date: str = None, max_pages: int = 20):
    """
    Scrape Hankyung Consensus Research Reports
    Target URL: https://consensus.hankyung.com/analysis/list
    """
    base_url = "https://consensus.hankyung.com/analysis/list"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    all_reports = []
    
    if not start_date:
        max_pages = 1
    
    start_dt = start_date if start_date else None
    end_dt = end_date if end_date else None
    
    for page in range(1, max_pages + 1):
        try:
            params = {
                "now_page": page,
                "pagenum": 80
            }
            if start_dt:
                params["sdate"] = start_dt
            if end_dt:
                params["edate"] = end_dt
                
            logger.info(f"Fetching Hankyung reports page {page}...")
            
            res = requests.get(base_url, params=params, headers=headers, timeout=10)
            res.encoding = 'utf-8' 
            
            if res.status_code != 200:
                logger.error(f"HTTP {res.status_code} on page {page}")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find("table")
            if not table:
                logger.warning(f"No table found on page {page}")
                break
                
            tbody = table.find("tbody")
            if not tbody:
                logger.warning(f"No tbody found on page {page}")
                break
                
            rows = tbody.find_all("tr")
            page_items_count = 0
            
            for row in rows:
                cols = row.find_all("td")
                if not cols or len(cols) < 6:
                    continue
                
                try:
                    date_str = cols[0].get_text(strip=True)
                    
                    if end_dt and date_str > end_dt:
                        continue
                    
                    if start_dt and date_str < start_dt:
                        logger.info(f"Reached date {date_str} older than start {start_dt}. Stopping.")
                        return all_reports
                    
                    category = cols[1].get_text(strip=True)
                    
                    title_td = cols[2]
                    title_a = title_td.find("a")
                    if not title_a:
                        continue
                        
                    full_title = title_a.get_text(strip=True)
                    link_suffix = title_a.get('href', '')
                    full_link = f"https://consensus.hankyung.com{link_suffix}" if link_suffix else ""
                    
                    # Extract stock name and code from title
                    stock_match = re.match(r'(.+?)\((\d+)\)\s+(.+)', full_title)
                    if stock_match:
                        stock_name = stock_match.group(1).strip()
                        stock_code = stock_match.group(2).strip()
                        title = stock_match.group(3).strip()
                    else:
                        stock_name = category
                        stock_code = ""
                        title = full_title
                    
                    author = cols[3].get_text(strip=True)
                    brokerage = cols[4].get_text(strip=True)
                    
                    pdf_td = cols[5]
                    pdf_a = pdf_td.find("a")
                    pdf_link = f"https://consensus.hankyung.com{pdf_a['href']}" if pdf_a and pdf_a.get('href') else ""
                    
                    all_reports.append({
                        "stock_name": stock_name,
                        "stock_code": stock_code,
                        "title": title,
                        "brokerage": brokerage,
                        "author": author,
                        "category": category,
                        "date": date_str,
                        "link": full_link,
                        "pdf_link": pdf_link,
                        "sentiment": analyze_sentiment(title)
                    })
                    page_items_count += 1
                    
                except Exception as e:
                    logger.error(f"Error parsing row: {e}")
                    continue
            
            logger.info(f"Hankyung page {page}: Found {page_items_count} reports")
            
            if page_items_count == 0:
                break
                
        except Exception as e:
            logger.error(f"Error on Hankyung page {page}: {e}")
            break
            
    return all_reports

def fetch_naver_reports(start_date: str = None, end_date: str = None, max_pages: int = 20):
    """
    Scrape Naver Finance Research - Company List
    Target URL: https://finance.naver.com/research/company_list.naver
    """
    base_url = "https://finance.naver.com/research/company_list.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    all_reports = []
    
    if not start_date:
        max_pages = 1
    
    # Naver uses YYYY.MM.DD format
    start_dt = start_date.replace("-", ".") if start_date else None
    end_dt = end_date.replace("-", ".") if end_date else None
    
    for page in range(1, max_pages + 1):
        try:
            url = f"{base_url}?&page={page}"
            logger.info(f"Fetching Naver reports page {page}...")
            
            res = requests.get(url, headers=headers, timeout=5)
            res.encoding = 'euc-kr' 
            
            if res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            box = soup.find("div", class_="box_type_m")
            if not box:
                tables = soup.find_all("table")
                table = tables[0] if tables else None
            else:
                table = box.find("table")
                
            if not table:
                break
                
            rows = table.find_all("tr")
            page_items_count = 0
            
            for row in rows:
                cols = row.find_all("td")
                if not cols or len(cols) < 5:
                    continue
                
                try:
                    # Parse Date
                    date_td = cols[4]
                    raw_date = date_td.get_text(strip=True)
                    full_date = "20" + raw_date if len(raw_date) == 8 else raw_date
                    
                    # Range Check
                    if end_dt and full_date > end_dt:
                        continue
                    
                    if start_dt and full_date < start_dt:
                        logger.info(f"Reached date {full_date} older than start {start_dt}. Stopping.")
                        return all_reports
                    
                    # Stock Name
                    stock_td = cols[0]
                    stock_name = stock_td.get_text(strip=True)
                    
                    # Title
                    title_td = cols[1]
                    title_a = title_td.find("a")
                    title = title_a.get_text(strip=True) if title_a else title_td.get_text(strip=True)
                    link_suffix = title_a['href'] if title_a else ""
                    full_link = f"https://finance.naver.com/research/{link_suffix}" if link_suffix else ""
                    
                    # Brokerage
                    brokerage_td = cols[2]
                    brokerage = brokerage_td.get_text(strip=True)
                    
                    # PDF
                    file_td = cols[3]
                    pdf_a = file_td.find("a")
                    pdf_link = pdf_a['href'] if pdf_a else ""
                    
                    all_reports.append({
                        "stock_name": stock_name,
                        "stock_code": "",  # Naver doesn't provide code in list
                        "title": title,
                        "brokerage": brokerage,
                        "author": "",  # Naver doesn't show author in list
                        "category": "기업",  # Naver company reports
                        "date": full_date,
                        "link": full_link,
                        "pdf_link": pdf_link,
                        "sentiment": analyze_sentiment(title)
                    })
                    page_items_count += 1
                    
                except Exception as e:
                    continue
            
            logger.info(f"Naver page {page}: Found {page_items_count} reports")
            
            if page_items_count == 0:
                pass
                
        except Exception as e:
            logger.error(f"Error on Naver page {page}: {e}")
            break
            
    return all_reports

def fetch_reports_sync(source: str = "hankyung", start_date: str = None, end_date: str = None, max_pages: int = 20):
    """
    Fetch reports from selected source
    """
    if source == "naver":
        return fetch_naver_reports(start_date, end_date, max_pages)
    else:
        return fetch_hankyung_reports(start_date, end_date, max_pages)

async def get_research_reports(source: str = "hankyung", start_date: str = None, end_date: str = None):
    """
    Async wrapper for scraping function with source selection.
    """
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, fetch_reports_sync, source, start_date, end_date)
    return data
