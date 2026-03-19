import asyncio
from datetime import datetime, timezone

# Diagnostic script to check emoji encoding and potential mismatches

MENU_BUTTONS_CODE = {
    "👥", "⏳", "📊", "➕", "⚙️", "🚀", "🎯", "📝", "📈", "🆘", "📜"
}

def check_emojis():
    # U+23F3 (⏳) vs U+231B (⌛)
    hourglass_1 = "⏳" # U+23F3
    hourglass_2 = "⌛" # U+231B
    
    print(f"Hourglass 1 (U+23F3): {hourglass_1.encode('unicode-escape')}")
    print(f"Hourglass 2 (U+231B): {hourglass_2.encode('unicode-escape')}")
    
    # Check for Variation Selector-16 (U+FE0F)
    gear = "⚙️"
    print(f"Gear (⚙️): {gear.encode('unicode-escape')}")
    
    # Check what's in builders.py (I'll simulate reading it)
    print("\nSimulated builders.py checks:")
    print(f"Requests (⏳): {'⏳'.encode('unicode-escape')}")

if __name__ == "__main__":
    check_emojis()
