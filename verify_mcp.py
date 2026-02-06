from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
import asyncio

async def run():
    print("Testing Stock Data MCP Server...")
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None # Inherit
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 1. List Tools
            tools = await session.list_tools()
            print(f"✅ Found {len(tools.tools)} tools: {[t.name for t in tools.tools]}")
            
            # 2. Call Tool: Search
            print("\n🔍 Calling Tool: search_stock('Samsung')")
            result = await session.call_tool("search_stock", arguments={"query": "Samsung"})
            print(f"Result: {str(result.content)[:100]}...")
            
            # 3. Call Tool: Price
            # Assuming we got a code from previous step, or just use 005930
            print("\n📈 Calling Tool: get_stock_price('005930')")
            result = await session.call_tool("get_stock_price", arguments={"code": "005930", "days": 3})
            print(f"Result: {str(result.content)}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
