import asyncio
import logging
from utils.gsheets_api import get_task_2_0

logging.basicConfig(level=logging.INFO)

async def verify_fix():
    # Day 7 is in the screenshot
    day = 7
    scenario = "Sovereign"
    print(f"--- Verifying Fix for Day {day}, Scenario {scenario} ---")
    
    task_data = await get_task_2_0(day, scenario)
    
    if not task_data:
        print("❌ Still no task data found.")
        return

    print("✅ Task Data Found:")
    for k, v in task_data.items():
        print(f"  {k}: {v[:50]}..." if v and len(v) > 50 else f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
