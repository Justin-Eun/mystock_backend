import asyncio
import stock_data_provider as provider

async def main():
    print("Testing provider...")
    res = await provider.get_stock_price("005930", "day")
    print(f"Name: {res.get('name')}")
    data = res.get('data', [])
    print(f"Count: {len(data)}")
    if len(data) > 0:
        print(f"First: {data[0]}")
        print(f"Last: {data[-1]}")
    else:
        print("No data.")

if __name__ == "__main__":
    asyncio.run(main())
