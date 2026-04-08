import asyncio
import os
from dotenv import load_dotenv
import sys
sys.path.append('.')
load_dotenv()
from utils.gsheets_api import get_all_values, SHEET_NAME_TASK_ENGINE

async def dump_tasks():
    print(f"--- Dumping Task Matrix for Day 20 ---")
    all_values = await get_all_values(SHEET_NAME_TASK_ENGINE)
    if not all_values:
        print("❌ Could not fetch Task Engine sheet")
        return

    # Find headers
    headers = all_values[0]
    print(f"Headers: {headers}")
    
    COL_DAY = 0
    COL_SCENARIO = 1
    
    found = False
    for i, row in enumerate(all_values[1:], start=2):
        if not row: continue
        if len(row) <= COL_DAY: continue
        
        day_str = str(row[COL_DAY]).strip()
        if day_str == "20":
            scenario = row[COL_SCENARIO] if len(row) > COL_SCENARIO else ""
            print(f"Row {i}: Day={day_str}, Scenario='{scenario}', Content Len={len(row)}")
            if len(row) > 2:
                print(f"   Name: {row[2]}")
            if len(row) > 7:
                print(f"   Light: {row[5]}")
                print(f"   Medium: {row[6]}")
                print(f"   Hard: {row[7]}")
            found = True
            
    if not found:
        print("❌ No entry found for Day 20 in the sheet.")

if __name__ == "__main__":
    asyncio.run(dump_tasks())
