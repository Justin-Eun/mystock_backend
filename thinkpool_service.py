import requests
import re
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

THINKPOOL_URL = "https://www.thinkpool.com/analysis/issue"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def get_ai_issue_data():
    """
    Fetches the 'AI Issue Capture' data from ThinkPool using Selenium.
    Returns a dictionary with 'issues' and 'timestamp'.
    """
    try:
        # Import here to avoid loading Selenium unless needed
        from thinkpool_scraper import get_ai_issue_data_selenium
        
        logger.info("Fetching ThinkPool data using Selenium scraper...")
        data = await get_ai_issue_data_selenium()
        
        return data

    except ImportError as e:
        logger.error(f"Selenium not available, falling back to simple scraper: {e}")
        # Fallback to original implementation
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, _fetch_html)
            
            if not content:
                return {"error": "Failed to fetch data"}

            data = _extract_nuxt_data(content)
            return data

        except Exception as e2:
            logger.error(f"Fallback scraper also failed: {e2}")
            return {"error": str(e2)}
    
    except Exception as e:
        logger.error(f"Error fetching ThinkPool data: {e}")
        return {"error": str(e)}


def _fetch_html():
    response = requests.get(THINKPOOL_URL, headers=HEADERS)
    response.raise_for_status()
    return response.text

def _extract_nuxt_data(content):
    """
    Parses the window.__NUXT__ object from HTML.
    Specific target: issue_list or similar structure containing 'is_str' (issue string).
    """
    try:
         # 1. Find the window.__NUXT__ block
        match = re.search(r'window\.__NUXT__=\(function\((.*?)\)\{return \{(.*?)\}\}\((.*?)\)\);', content)
        if not match:
            logger.warning("Could not find window.__NUXT__ pattern.")
            return {"issues": []}

        # The NUXT data is executed as a function. 
        # Simpler approach: Extract distinct issue objects using regex directly on the whole content 
        # because parsing the full minified JS object in Python is fragile.
        
        # Pattern: {issn:123,is_str:"Keyword",...}
        # Note: keys might be unquoted.
        
        # Let's extract 'is_str' and 'issn' pairs.
        # We assume the list is ordered by rank/importance as it appears in the array.
        
        # Regex to capture objects that have 'issn' and 'is_str'
        # Example: {issn:356,is_str:"남북경협",source:b}
        
        # We start by finding all such patterns.
        # Allow for variations in spacing and property order if possible, but NUXT output is usually machine-generated and consistent.
        
        pattern = re.compile(r'\{issn:(\d+),is_str:"(.*?)"')
        matches = pattern.findall(content)
        
        issues = []
        seen = set()
        
        for issn, keyword in matches:
            if issn not in seen:
                issues.append({
                    "id": int(issn),
                    "keyword": keyword,
                    "rank": len(issues) + 1
                })
                seen.add(issn)
        
        # Limit to top 20 or so
        return {
            "issues": issues[:20],
            "total_count": len(issues)
        }

    except Exception as e:
        logger.error(f"Error parsing regex: {e}")
        return {"issues": []}
