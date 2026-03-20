import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

# Diagnostic script to verify database queries

def run_diag():
    print("🔥 Starting Database Diagnosis...")
    
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("credentials.json") if os.path.exists("credentials.json") else None
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized.")
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return

    try:
        db = firestore.client(database_id="(default)")
        print(f"✅ Client created for database: {db._database}")
        
        # Test 1: Count users
        count = db.collection("users").count().get()[0][0].value
        print(f"📊 Total users: {count}")
        
        # Test 2: Get pending users
        print("🔍 Testing 'pending' query...")
        pending = db.collection("users").where("status", "==", "pending").limit(5).stream()
        p_list = [d.id for d in pending]
        print(f"✅ Found {len(p_list)} pending users: {p_list}")
        
        # Test 3: Get active users
        print("🔍 Testing 'active' query...")
        active = db.collection("users").where("status", "==", "active").limit(5).stream()
        a_list = [d.id for d in active]
        print(f"✅ Found {len(a_list)} active users: {a_list}")
        
        # Test 4: Global settings
        print("🔍 Testing 'settings/global'...")
        settings = db.collection("settings").document("global").get()
        if settings.exists:
            print(f"✅ Settings found: {settings.to_dict().keys()}")
        else:
            print("⚠️ Settings document DOES NOT EXIST.")
            
    except Exception as e:
        print(f"❌ Query failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diag()
