import asyncio
from utils.gsheets_api import sync_gsheets_to_firestore

async def main():
    print("Starting sync...")
    count = await sync_gsheets_to_firestore()
    print(f"Sync complete. Cached {count} tasks.")

if __name__ == "__main__":
    asyncio.run(main())
