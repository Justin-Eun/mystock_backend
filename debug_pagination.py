import requests
from bs4 import BeautifulSoup
import time

def check_page(page):
    url = f"https://finance.naver.com/research/company_list.naver?&page={page}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
    
    # Get first row date
    box = soup.find("div", class_="box_type_m")
    if box:
        table = box.find("table")
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                date_td = cols[4]
                print(f"Page {page} First Item Date: {date_td.get_text(strip=True)}")
                return
    print(f"Page {page}: No data found")

if __name__ == "__main__":
    check_page(1)
    check_page(2)
    check_page(10)
