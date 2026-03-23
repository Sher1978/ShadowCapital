from datetime import datetime, timedelta, timezone
import logging

def get_now_in_tz(tz_str="UTC+7"):
    """Returns the current time in the specified timezone string (e.g. 'UTC+3', 'UTC+7')."""
    now_utc = datetime.now(timezone.utc)
    try:
        # Simple parsing for UTC+X or UTC-X
        if not tz_str or not isinstance(tz_str, str):
            tz_str = "UTC+7"
        
        clean_tz = tz_str.strip().upper()
        if clean_tz == "UTC":
            return now_utc
            
        offset_str = clean_tz.replace("UTC", "").replace("+", "")
        offset = int(offset_str)
        return now_utc + timedelta(hours=offset)
    except Exception as e:
        logging.warning(f"Failed to parse timezone '{tz_str}', defaulting to UTC+7: {e}")
        return now_utc + timedelta(hours=7)

def adjust_to_tz(dt, tz_str="UTC+7"):
    """
    Adjusts a datetime object to the specified timezone string.
    If dt is naive, it's assumed to be UTC or adjusted based on offset.
    """
    if not dt:
        return dt
        
    try:
        if not tz_str or not isinstance(tz_str, str):
            tz_str = "UTC+7"
            
        clean_tz = tz_str.strip().upper()
        offset_str = clean_tz.replace("UTC", "").replace("+", "")
        offset = int(offset_str)
        
        # If dt is aware but not UTC, convert to UTC first? 
        # Actually in this bot, most are UTC-aware (Firestore).
        if dt.tzinfo:
            # Shift to UTC then add offset
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc + timedelta(hours=offset)
        else:
            # Naive: assume it was UTC-equivalent and just add offset
            return dt + timedelta(hours=offset)
    except Exception as e:
        logging.warning(f"Failed to adjust datetime to '{tz_str}': {e}")
        return dt
