import openai
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging

# Configure Logging
logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def analyze_stock(stock_name: str, price_data, financials):
    last_close = price_data[-1]['close'] if price_data else "Unknown"
    
    prompt = f"""
    Analyze the investment value of {stock_name} based on the following data:
    
    Recent Price Trend: {last_close} KRW (Last close)
    Financials: {financials}
    
    Provide a concise investment outlook (Buy/Sell/Hold) and key reasons.
    Output in Korean.
    """

    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key":
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

    if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key":
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    return "AI API Key not configured. Please add OPENAI_API_KEY or GEMINI_API_KEY to .env file."

import json

# ... helper functions module level ...

def create_fallback(data):
    items = []
    titles = {
        "US_10Y": "미국 10년물 국채 금리",
        "DXY": "달러 인덱스",
        "USD_KRW": "원/달러 환율",
        "VIX": "VIX 지수",
        "BTC": "비트코인",
        "ES_F": "S&P500",
        "NQ_F": "나스닥100",
        "WTI": "국제 유가 (WTI)",
        "NVDA": "엔비디아",
        "TSLA": "테슬라",
        "FearGreed": "공포 & 탐욕 지수",
        "KoreanCDS": "한국 CDS 프리미엄"
    }
    
    for key, val in data.items():
        if not val: continue
        
        change = val.get('change', 0)
        status = "상승" if change > 0 else "하락" if change < 0 else "보합"
        if abs(change) < 0.05 and key != "BTC": status = "보합" # Fuzzy flat
        
        items.append({
            "id": key,
            "title": titles.get(key, key),
            "status": status,
            "interpretation": "데이터 기반 자동 생성 (AI 미사용)"
        })
    
    # Sort to match standard order if possible
    order = ["US_10Y", "DXY", "USD_KRW", "VIX", "FearGreed", "BTC", "ES_F", "NQ_F", "WTI", "NVDA", "TSLA", "KoreanCDS"]
    items.sort(key=lambda x: order.index(x['id']) if x['id'] in order else 99)
    
    return {
        "summary_title": "시장 데이터 (실시간)",
        "summary_content": "AI 분석 서비스를 사용할 수 없어 기본 데이터를 표시합니다.",
        "items": items
    }

async def generate_with_openai(prompt):
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key":
        return None
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o", # Use 4o or 3.5-turbo
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        return json.loads(text)
    except Exception as e:
        logger.error(f"[ERROR] OpenAI Generation Failed: {e}")
        return None

async def generate_with_gemini(prompt):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key":
        return None
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # gemini-pro is deprecated/404, using 1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash') 
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        return json.loads(text)
    except Exception as e:
        logger.error(f"[ERROR] Gemini Generation Failed: {e}")
        return None

async def generate_market_briefing(market_data):
    """
    Generate a market briefing based on the provided data.
    """
    
    # Format data for prompt
    data_str = json.dumps(market_data, indent=2)
    current_date = "2026-01-28" # Should be dynamic ideally
    
    prompt = f"""
    You are a professional financial analyst. Based on the following market data (Date: {current_date}), write a "Global Economic Briefing" in Korean.
    
    Market Data:
    {data_str}
    
    Structure your response as a valid JSON object with the following keys:
    1. "summary_title": A short catchy title (e.g. "Rates & Dollar High, Volatility Returns")
    2. "summary_content": A 3-4 line summary of the overall market situation.
    3. "items": A list of objects for each of the following 10 items (if data exists):
       - US_10Y, DXY, USD_KRW, VIX, FearGreed, BTC, Futures, WTI, Leaders, KoreanCDS
       - Each item should have:
         - "id": key from the input
         - "title": Display title (e.g. "미국 10년물 국채 금리")
         - "status": Short status string (e.g. "상승", "보합", "하락")
         - "interpretation": A concise interpretation (2 lines max) of what this means for the market.
    
    Make the tone professional yet accessible.
    IMPORTANT: Return ONLY the JSON object. Do not wrap in markdown code blocks.
    """

    # execution flow
    result = await generate_with_openai(prompt)
    if result: return result
    
    result = await generate_with_gemini(prompt)
    if result: return result

    logger.warning("[WARN] All AI services failed. Using fallback.")
    return create_fallback(market_data)


async def chat_with_agent(message: str, history: list, context: dict):
    """
    Handles chat interaction with the AI agent.
    
    Args:
        message: The user's current message.
        history: List of previous messages [{"role": "user", "content": "..."}, ...]
        context: Current state (stock name, price, financials, analysis)
    """
    
    # 1. Construct System Prompt with Context
    stock_info = ""
    if context.get("stockName"):
        stock_info = f"""
        User is currently viewing: {context['stockName']} ({context.get('stockCode', 'N/A')})
        
        Current Data:
        - Recent Price Data (Last 5 days): {str(context.get('stockData', [])[-5:])}
        - Financials: {str(context.get('financials', 'Not loaded'))}
        - AI Analysis Summary: {context.get('analysis', 'Not available')}
        """
    else:
        stock_info = "User is currently at the Dashboard (no specific stock selected)."

    system_prompt = f"""
    You are an expert financial analyst AI assistant embedded in a stock dashboard application.
    Your goal is to help users understand market trends, analyze specific stocks, and answer financial questions.
    
    Context:
    {stock_info}
    
    Guidelines:
    1. Be concise and professional but friendly.
    2. Use the provided Context to answer detailed questions about the stock on screen.
    3. If the user asks about a stock you are NOT viewing, use your general knowledge but mention you are referring to general knowledge.
    4. You can use Markdown tables or lists to format data.
    5. Respond in Korean (Natural and professional tone).
    6. Disclaimer: Always remind users that this is not financial advice if they ask for specific buy/sell recommendations.
    """

    # 2. Prepare Messages
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add limited history (last 10 messages to save context window)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": message})

    # 3. Call AI Service (OpenAI first, then Gemini)
    if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key":
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4", # Use GPT-4 for better reasoning context
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[ERROR] OpenAI Chat Failed: {e}")

    if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key":
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-pro') # Use Pro for reasoning
            
            # Gemini has a different chat structure, but for single turn with history, we can just pack it
            # Or use start_chat. Let's strictly map to content generation for simplicity or use pure convert
            # For simplicity in this hybrid setup, we'll format it as a single prompt for Gemini if history apis are complex,
            # but Gemini supports chat history. Let's do a simple prompt concatenation for fallback robustness.
            
            full_prompt = system_prompt + "\n\nConversation History:\n"
            for msg in messages[1:]:
                full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
            full_prompt += "\nASSISTANT:"
            
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"[ERROR] Gemini Chat Failed: {e}")

    return "죄송합니다. 현재 AI 서버에 연결할 수 없습니다."
