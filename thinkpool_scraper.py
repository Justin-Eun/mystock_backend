"""
ThinkPool Browser Automation Scraper

Uses Selenium to execute JavaScript and extract dynamically loaded content
from ThinkPool's AI Issue Analysis page.
"""

import logging
import os
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

THINKPOOL_MAIN_URL = "https://www.thinkpool.com/analysis/issue"

def get_headless_driver():
    """Initialize headless Chrome driver with optimized options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_nuxt_data(driver):
    """Extract window.__NUXT__ data from page source"""
    try:
        page_source = driver.page_source
        pattern = re.compile(r'window\.__NUXT__=\(function\((.*?)\)\{return \{(.*?)\}\}\((.*?)\)\);', re.DOTALL)
        match = pattern.search(page_source)
        
        if not match:
            logger.warning("Could not find window.__NUXT__ pattern")
            return None
        
        # Extract keyword data using simpler regex
        keyword_pattern = re.compile(r'\{issn:(\d+),is_str:"(.*?)"')
        keywords = keyword_pattern.findall(page_source)
        
        issues = []
        seen = set()
        
        for issn, keyword in keywords:
            if issn not in seen:
                issues.append({
                    "id": int(issn),
                    "keyword": keyword,
                    "rank": len(issues) + 1
                })
                seen.add(issn)
        
        return issues[:20]
    
    except Exception as e:
        logger.error(f"Error extracting NUXT data: {e}")
        return []

def scrape_issue_list():
    """Scrape main issue list from ThinkPool"""
    driver = None
    try:
        driver = get_headless_driver()
        logger.info(f"Loading {THINKPOOL_MAIN_URL}")
        
        driver.get(THINKPOOL_MAIN_URL)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(2)  # Allow JavaScript to execute
        
        issues = extract_nuxt_data(driver)
        
        logger.info(f"Extracted {len(issues)} issues")
        return {
            "issues": issues,
            "total_count": len(issues)
        }
        
    except Exception as e:
        logger.error(f"Error scraping issue list: {e}")
        return {"issues": [], "error": str(e)}
    
    finally:
        if driver:
            driver.quit()

def capture_bubble_chart(issn):
    """Capture bubble chart visualization from main page for a specific issue"""
    driver = None
    try:
        driver = get_headless_driver()
        main_url = f"{THINKPOOL_MAIN_URL}?issn={issn}"
        
        logger.info(f"Loading main page for bubble chart: {main_url}")
        driver.get(main_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(4)  # Wait for JavaScript and bubble chart to render
        
        # Try to find and capture the bubble chart container
        bubble_chart_url = None
        try:
            # Try multiple selectors for bubble chart area
            selectors = [
                ".issue_graph",  # Common container for issue visualizations
                ".bubble_chart",
                "#bubbleChart",
                "[class*='bubble']",
                "[class*='graph']"
            ]
            
            chart_element = None
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and elements[0].is_displayed():
                        chart_element = elements[0]
                        logger.info(f"Found bubble chart using selector: {selector}")
                        break
                except:
                    continue
            
            # If specific element not found, capture viewport area
            if not chart_element:
                logger.info("Bubble chart element not found, capturing viewport")
            
            # Save screenshot
            import os
            screenshot_dir = os.path.join(os.path.dirname(__file__), "../frontend/public/charts")
            os.makedirs(screenshot_dir, exist_ok=True)
            
            screenshot_path = os.path.join(screenshot_dir, f"bubble_{issn}.png")
            
            if chart_element:
                chart_element.screenshot(screenshot_path)
            else:
                driver.save_screenshot(screenshot_path)
            
            bubble_chart_url = f"/charts/bubble_{issn}.png"
            logger.info(f"Bubble chart saved: {screenshot_path}")
            
        except Exception as e:
            logger.warning(f"Could not capture bubble chart: {e}")
        
        return bubble_chart_url
        
    except Exception as e:
        logger.error(f"Error capturing bubble chart: {e}")
        return None
    
    finally:
        if driver:
            driver.quit()

def scrape_issue_detail(issn):
    """Scrape detailed information for a specific issue"""
    driver = None
    try:
        driver = get_headless_driver()
        detail_url = f"https://www.thinkpool.com/analysis/issue/detail?issn={issn}"
        
        logger.info(f"Loading detail page: {detail_url}")
        driver.get(detail_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(3)  # Allow JavaScript to fully execute
        
        # Extract headline and summary from page source
        page_source = driver.page_source
        
        # Look for hl_str (headline) and hl_cont (content) in NUXT data
        hl_match = re.search(r'hl_str:\\"(.*?)\\"', page_source)
        cont_match = re.search(r'hl_cont:\\"(.*?)\\"', page_source)
        
        headline = hl_match.group(1) if hl_match else ""
        summary = cont_match.group(1) if cont_match else ""
        
        # Clean up escaped characters
        headline = headline.replace('\\"', '"').replace('\\/', '/')
        summary = summary.replace('\\"', '"').replace('\\/', '/').replace('\\u003C', '<').replace('\\u003E', '>')
        
        # Try to extract related stocks from rendered page
        related_stocks = []
        try:
            # Wait for the tab content to potentially load
            time.sleep(2)
            
            # Look for stock elements in the page
            stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_item, .related_stock, td.stock")
            
            for elem in stock_elements[:5]:  # Limit to top 5
                try:
                    text = elem.text.strip()
                    if text and len(text) < 50:  # Basic validation
                        related_stocks.append(text)
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not extract related stocks: {e}")
        # Capture full page screenshot (chart element detection is unreliable)
        chart_image_url = None
        try:
            # Wait for page to fully render
            time.sleep(5)
            
            # Save full page screenshot to frontend public directory
            import os
            screenshot_dir = os.path.join(os.path.dirname(__file__), "../frontend/public/charts")
            os.makedirs(screenshot_dir, exist_ok=True)
            
            screenshot_path = os.path.join(screenshot_dir, f"chart_{issn}.png")
            driver.save_screenshot(screenshot_path)
            
            # Return URL relative to frontend public
            chart_image_url = f"/charts/chart_{issn}.png"
            logger.info(f"Page screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not capture screenshot: {e}")
        
        return {
            "issn": issn,
            "headline": headline,
            "summary": summary,
            "related_stocks": related_stocks,
            "chart_image": chart_image_url
        }
        
    except Exception as e:
        logger.error(f"Error scraping issue detail {issn}: {e}")
        return {
            "issn": issn,
            "error": str(e)
        }
    
    finally:
        if driver:
            driver.quit()

async def get_ai_issue_data_selenium():
    """
    Main entry point for getting AI issue data using Selenium.
    Captures bubble chart from main page and detail screenshots.
    """
    try:
        # Get main issue list
        data = scrape_issue_list()
        
        if not data.get("issues"):
            return {"error": "No issues found"}
        
        # For top 3 issues, get detailed data including screenshots
        issues_to_detail = data["issues"][:3]
        
        for idx, issue in enumerate(issues_to_detail):
            detail = scrape_issue_detail(issue["id"])
            
            # Enrich issue with detail data
            if "headline" in detail:
                issue["headline"] = detail["headline"]
                issue["summary"] = detail["summary"]
                issue["related_stocks"] = detail.get("related_stocks", [])
                issue["detail_image"] = detail.get("chart_image")  # Renamed for clarity
            
            # For the first issue, also capture bubble chart from main page
            if idx == 0:
                bubble_url = capture_bubble_chart(issue["id"])
                if bubble_url:
                    issue["bubble_chart_image"] = bubble_url
        
        return data
        
    except Exception as e:
        logger.error(f"Error in get_ai_issue_data_selenium: {e}")
        return {"error": str(e), "issues": []}
