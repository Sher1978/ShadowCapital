from utils.timezone_utils import get_user_current_day
from datetime import datetime, timezone, timedelta

def test():
    # Sprint starts April 1st, 2026, 20:00 UTC (which is April 2nd, 03:00 Moscow/Vietnam approx)
    # Actually, let's say it starts April 1st, 10:00 UTC.
    start_date = datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)
    
    # Test cases for Vietnam (UTC+7)
    # 1. April 1st, 23:00 UTC (April 2nd, 06:00 Vietnam)
    now1 = datetime(2026, 4, 1, 23, 0, tzinfo=timezone.utc)
    day1 = get_user_current_day(start_date, "UTC+7", now_override=now1)
    print(f"VN Case 1 (Apr 2 Morning): Expected Day 2, Got Day {day1}")
    
    # 2. April 2nd, 10:00 UTC (April 2nd, 17:00 Vietnam) - Same day!
    now2 = datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)
    day2 = get_user_current_day(start_date, "UTC+7", now_override=now2)
    print(f"VN Case 2 (Apr 2 Evening): Expected Day 2, Got Day {day2}")

    # Test cases for Moscow (UTC+3)
    # 1. April 1st, 23:00 UTC (April 2nd, 02:00 Moscow)
    day3 = get_user_current_day(start_date, "UTC+3", now_override=now1)
    print(f"MSK Case 1 (Apr 2 Night): Expected Day 2, Got Day {day3}")

if __name__ == "__main__":
    test()
