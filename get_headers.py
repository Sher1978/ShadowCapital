import asyncio
from utils.gsheets_api import get_gsheets_client
from config import GOOGLE_SHEET_URL

async def get_headers():
    client = get_gsheets_client()
    sh = client.open_by_url(GOOGLE_SHEET_URL)
    worksheet = sh.worksheet("NEW_TASK_ENGINE")
    headers = worksheet.row_values(1)
    print(f"HEADERS_START:{headers}:HEADERS_END")

if __name__ == "__main__":
    asyncio.run(get_headers())
