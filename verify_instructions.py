import asyncio
import logging
from utils.gsheets_api import get_instruction_text

logging.basicConfig(level=logging.INFO)

async def verify_instructions():
    print("--- Verifying Instruction Fetching ---")
    
    # This should return the default from utils/texts.py if the sheet doesn't exist
    text = await get_instruction_text()
    
    if not text:
        print("❌ No instruction text found.")
        return

    print("✅ Instruction Text Found (First 100 chars):")
    print(text[:100] + "...")
    
    if "Добро пожаловать в Shershadow 2.0" in text:
        print("✅ Default text correctly loaded.")
    else:
        print("⚠️ Text loaded but doesn't match default. This might be correct if GSheets has data.")

if __name__ == "__main__":
    asyncio.run(verify_instructions())
