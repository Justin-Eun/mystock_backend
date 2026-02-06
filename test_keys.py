from dotenv import load_dotenv
import os
import asyncio
import openai

# Force reload env
load_dotenv(override=True)

async def test():
    key = os.getenv('OPENAI_API_KEY')
    print(f"OpenAI Key: {key[:20]}...")
    
    try:
        client = openai.OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("Success:", response.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
