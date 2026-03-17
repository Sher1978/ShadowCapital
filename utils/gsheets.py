import aiohttp
import csv
import io
import logging
from config import GOOGLE_SHEET_URL

async def fetch_daily_tasks():
    """
    Fetches the daily tasks from the Google Sheet as a CSV.
    """
    # Replace /edit with /export?format=csv
    csv_url = GOOGLE_SHEET_URL.split("/edit")[0] + "/export?format=csv"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(csv_url) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                else:
                    logging.error(f"Failed to fetch Google Sheet: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Error fetching Google Sheet: {e}")
        return None

async def get_task_for_day(day_number: int, quality_name: str) -> str:
    """
    Returns the task text for a specific day, replacing placeholders.
    """
    content = await fetch_daily_tasks()
    if not content:
        return "Задание на сегодня еще не готово. Продолжай практиковать прошлое!"

    f = io.StringIO(content)
    reader = csv.DictReader(f)
    
    tasks = {int(row['День']): row['Задание (Task_Body)'] for row in reader if row['День'].isdigit()}
    
    # If specific day task is missing, find the closest previous day (as tasks might be for chunks of days)
    target_task = tasks.get(day_number)
    if not target_task:
        # Sort days and find the largest day <= day_number
        available_days = sorted(tasks.keys())
        prev_day = 1
        for d in available_days:
            if d <= day_number:
                prev_day = d
            else:
                break
        target_task = tasks.get(prev_day)

    if target_task:
        return target_task.replace("[Качество]", quality_name).replace("[качество]", quality_name)
    
    return f"День {day_number}: Продолжай интеграцию твоего качества {quality_name}!"
