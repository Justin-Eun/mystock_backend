import openai
import google.generativeai as genai
import os
from dotenv import load_dotenv

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
