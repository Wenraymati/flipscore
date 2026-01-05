import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.services.price_client import PriceClient

async def main():
    client = PriceClient()
    product = "iPhone XR 64GB"
    print(f"Searching for: {product}...")
    
    data = await client.fetch_market_data(product)
    
    print("\n--- Market Data Results ---")
    print(f"Source: {data.get('source')}")
    print(f"Items found: {data.get('count')}")
    print(f"Min Price: ${data.get('min'):,}")
    print(f"Max Price: ${data.get('max'):,}")
    print(f"Average: ${data.get('avg'):,}")
    print(f"Median: ${data.get('median'):,}")
    print(f"Sample Prices: {data.get('prices_sample')}")
    
    if data.get("count") == 0:
        print("\n⚠️ SYSTEM WARNING: No data found. Check if API is blocking requests (403) or if product query is bad.")

if __name__ == "__main__":
    asyncio.run(main())
