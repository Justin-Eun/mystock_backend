import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/research/company_list.naver"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

try:
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    # Naver Finance usually produces euc-kr
    # but requests might auto detect. Let's force it if needed.
    # res.encoding = 'euc-kr' 
    
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Inspect table
    # Usually it's in a specific class or check all tables
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables.")
    
    for i, table in enumerate(tables):
        print(f"--- Table {i} ---")
        # Print first few rows to identify
        rows = table.find_all('tr')
        for r in rows[:5]:
            print(r.get_text(strip=True)[:100])

except Exception as e:
    print(f"Error: {e}")
