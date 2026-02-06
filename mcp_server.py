from mcp.server.fastmcp import FastMCP
import asyncio
import json
import sys
import os

# --- STDOUT GUARD START ---
# Redirect all stdout to stderr to prevent libraries from breaking MCP protocol
original_stdout = sys.stdout
sys.stdout = sys.stderr

import stock_data_provider as data_service
import ai_service

# Restore stdout for MCP communication
sys.stdout = original_stdout
# --- STDOUT GUARD END ---

# Initialize FastMCP Server
mcp = FastMCP("StockDataMCP")

# 1. Search Tool
@mcp.tool()
async def search_stock(query: str) -> str:
    """
    Search for a stock by name or code.
    Returns a list of matches with Name, Code, and Exchange.
    """
    results = await data_service.search_stock(query)
    if not results:
        return "No stocks found."
    return json.dumps(results, ensure_ascii=False)

# 2. Price Tool
@mcp.tool()
async def get_stock_price(code: str, days: int = 5) -> str:
    """
    Get recent stock price history.
    Args:
        code: Stock code (e.g., '005930', 'TSLA')
        days: Number of recent days to fetch (default: 5)
    """
    # Calculate start date based on days? 
    # For simplicity, we just fetch 'day' timeframe and slice the last N items
    data = await data_service.get_stock_price(code, "day", None, None)
    
    # Handle response structure
    if isinstance(data, dict) and "data" in data:
        prices = data["data"][-days:]
        name = data.get("name", code)
        return f"Stock: {name}\nPrices: {json.dumps(prices, ensure_ascii=False)}"
    elif isinstance(data, list):
        prices = data[-days:]
        return f"Stock: {code}\nPrices: {json.dumps(prices, ensure_ascii=False)}"
    
    return "Failed to fetch price data."

# 3. Financials Tool
@mcp.tool()
async def get_financials(code: str) -> str:
    """
    Get key financial indicators (P/E, P/B, Dividend Yield, etc.)
    Args:
        code: Stock code
    """
    financials = await data_service.get_financials(code)
    if not financials:
        return "Financial data not available."
    return json.dumps(financials, ensure_ascii=False)

# 4. Market Briefing Tool
@mcp.tool()
async def get_market_briefing() -> str:
    """
    Get a global market briefing (Indices, Commodities, AI Analysis).
    """
    indices = await data_service.get_global_market_indices()
    # Ideally reuse the AI briefing logic too
    briefing = await ai_service.generate_market_briefing(indices)
    return json.dumps(briefing, ensure_ascii=False)

if __name__ == "__main__":
    # Run via stdio for local agent connection
    mcp.run(transport='stdio')
