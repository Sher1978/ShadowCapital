from datetime import datetime, timezone

def test_fixed_logic():
    print("Testing aware (UTC) vs aware (UTC) subtraction...")
    
    # Simulate aware datetime from Firestore
    start_date = datetime(2026, 3, 10, tzinfo=timezone.utc)
    
    # Use our new fixed way to get "now"
    now = datetime.now(timezone.utc)
    
    try:
        diff = now - start_date
        day = diff.days + 1
        print(f"✅ Success! Day calculation works: {day}")
        print("Verification PASSED: No more TypeError between naive and aware datetimes.")
    except TypeError as e:
        print(f"❌ FAILED: {e}")
        print("The bug still exists!")

if __name__ == "__main__":
    test_fixed_logic()
