import asyncio
import os
from dotenv import load_dotenv
import ai_service

# Load env for keys
load_dotenv()

async def test_chat():
    print("Testing Chat Agent...")
    
    # Mock Context
    context = {
        "stockName": "Samsung Electronics",
        "stockCode": "005930",
        "stockData": [{"date": "2024-01-01", "close": 70000}, {"date": "2024-01-02", "close": 71000}],
        "financials": {"P/E": 15.5},
        "analysis": "Strong Buy based on memory chip recovery."
    }
    
    history = []
    message = "이 주식의 P/E는 얼마인가요?"
    
    print(f"User: {message}")
    print(f"Context: {context['stockName']}, P/E: {context['financials']['P/E']}")
    
    response = await ai_service.chat_with_agent(message, history, context)
    
    print(f"Agent: {response}")
    
    if "15.5" in response or "십오점오" in response:
        print("✅ SUCCESS: Agent used context correctly.")
    else:
        print("⚠️ WARNING: Agent might not have used context (or API key missing).")

if __name__ == "__main__":
    asyncio.run(test_chat())
