import asyncio
import logging
from utils.gsheets_api import get_gsheets_client
from config import GOOGLE_SHEET_URL

logging.basicConfig(level=logging.INFO)

async def debug_sheet():
    day = 7
    scenario = "Sovereign"
    print(f"--- Debugging Sheet for Day {day}, Scenario {scenario} ---")
    
    client = get_gsheets_client()
    if not client:
        print("❌ Client failed")
        return
        
    sh = client.open_by_url(GOOGLE_SHEET_URL)
    worksheet = sh.worksheet("NEW_TASK_ENGINE")
    
    # Check headers
    headers = worksheet.row_values(1)
    print(f"Headers: {headers}")
    
    records = worksheet.get_all_records()
    print(f"Total records: {len(records)}")
    
    if records:
        print(f"Sample record keys: {list(records[0].keys())}")
        for r in records:
            if str(r.get('Day')) == str(day):
                print(f"Match found: {r}")

if __name__ == "__main__":
    asyncio.run(debug_sheet())
