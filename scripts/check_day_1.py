import asyncio
import sys
sys.path.append('.')
from utils.gsheets_api import get_task_2_0

async def check():
    try:
        t = await get_task_2_0(1, 'Sovereign')
        print(f"Day 1 Sovereign: {t}")
    except Exception as e:
        print(f"Error Day 1: {e}")
        
    try:
        t = await get_task_2_0(2, 'Sovereign')
        print(f"Day 2 Sovereign: {t}")
    except Exception as e:
        print(f"Error Day 2: {e}")

if __name__ == "__main__":
    asyncio.run(check())
