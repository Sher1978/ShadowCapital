import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred_path = "credentials.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logging.info("✅ Firebase Admin initialized with credentials.json")
        else:
            firebase_admin.initialize_app()
            logging.info("✅ Firebase Admin initialized with Application Default Credentials")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Firebase Admin: {e}")

# Use Synchronous Client due to local async hangs
database_id_env = os.getenv("FIREBASE_DATABASE_ID", "(default)")
# In Google Cloud SDK, the default database is targeted by None or (default) 
# but (default) as a string can sometimes fail depending on SDK version.
# We'll normalize it here.
target_db = None if database_id_env == "(default)" else database_id_env

db = firestore.client(database_id=target_db)
# Secondary client specifically for SFI Diagnostic results in (default) database
db_sfi = firestore.client(database_id=None) 
project_id = os.getenv("FIREBASE_PROJECT_ID", "shershadow")
logging.info(f"🔥 Sync Firestore client created for project: {project_id}, database: {database_id_env}")
logging.info(f"🔥 SFI Firestore client created for project: {project_id}, database: (default)")

class FirestoreDB:
    db = db  # Expose the client
    
    @staticmethod
    async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user by Telegram ID (Sync wrapper)."""
        # Using sync call because async hangs locally
        query = db.collection("users").where("tg_id", "==", tg_id).limit(1)
        docs = list(query.stream())
        if docs:
            data = docs[0].to_dict()
            data['id'] = docs[0].id
            return data
        return None

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> str:
        """Create a new user document (Sync wrapper)."""
        user_data['created_at'] = datetime.now(timezone.utc)
        _, doc_ref = db.collection("users").add(user_data)
        return doc_ref.id

    @staticmethod
    async def update_user(doc_id: str, update_data: Dict[str, Any]):
        """Update user fields (Sync wrapper)."""
        db.collection("users").document(doc_id).update(update_data)

    @staticmethod
    async def add_log(user_doc_id: str, log_data: Dict[str, Any]) -> str:
        """Add a shadow log for a user (Sync wrapper)."""
        log_data['created_at'] = datetime.now(timezone.utc)
        _, doc_ref = db.collection("users").document(user_doc_id).collection("logs").add(log_data)
        return doc_ref.id

    @staticmethod
    async def get_log(user_doc_id: str, log_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific log by ID (Sync wrapper)."""
        doc = db.collection("users").document(user_doc_id).collection("logs").document(log_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    @staticmethod
    async def get_logs(user_doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs for a user (Sync wrapper)."""
        query = db.collection("users").document(user_doc_id).collection("logs") \
                  .order_by("created_at", direction=firestore.Query.DESCENDING) \
                  .limit(limit)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]

    @staticmethod
    async def get_today_log(user_doc_id: str) -> Optional[Dict[str, Any]]:
        """Check if there's a log for the current UTC day (Sync wrapper)."""
        # Note: timezone-naive datetime comparison might need care but keeping it similar to original
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        query = db.collection("users").document(user_doc_id).collection("logs") \
                  .where("created_at", ">=", today_start) \
                  .limit(1)
        docs = list(query.stream())
        if docs:
            return docs[0].to_dict()
        return None

    @staticmethod
    async def get_global_settings() -> Dict[str, Any]:
        """Fetch global settings (Sync wrapper)."""
        logging.info("🔥 FirestoreDB.get_global_settings: Attempting to fetch 'settings/global'...")
        try:
            doc = db.collection("settings").document("global").get()
            if doc.exists:
                data = doc.to_dict()
                logging.info(f"🔥 Found global settings: {data}")
                return data
            else:
                logging.warning("🔥 Global settings not found in Firestore, using defaults.")
                defaults = {
                    "morning_time": "09:00",
                    "deadline_time": "20:30",
                    "evening_time": "21:30",
                    "sunday_time": "18:00"
                }
                db.collection("settings").document("global").set(defaults)
                return defaults
        except Exception as e:
            logging.error(f"🔥 Error in get_global_settings: {e}", exc_info=True)
            return {
                "morning_time": "09:00",
                "deadline_time": "20:30",
                "evening_time": "21:30",
                "sunday_time": "18:00"
            }

    @staticmethod
    async def update_global_settings(update_data: Dict[str, Any]):
        """Update global settings (Sync wrapper)."""
        db.collection("settings").document("global").update(update_data)

    @staticmethod
    async def get_active_users() -> List[Dict[str, Any]]:
        """Get all active users for scheduler (Sync wrapper)."""
        query = db.collection("users").where("status", "==", "active")
        docs = query.stream()
        users = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            users.append(d)
        return users

    @staticmethod
    async def save_tasks_matrix(tasks_list: List[Dict[str, Any]]):
        """Overwrite the tasks_matrix collection with fresh data."""
        batch = db.batch()
        # Delete existing tasks first (simplified - limit 500)
        old_tasks = db.collection("tasks_matrix").limit(500).stream()
        for doc in old_tasks:
            batch.delete(doc.reference)
        
        # Add new tasks
        for task in tasks_list:
            doc_id = f"day_{task['day']}_{task.get('scenario', 'all')}"
            doc_ref = db.collection("tasks_matrix").document(doc_id)
            batch.set(doc_ref, task)
        
        batch.commit()
        # Update last sync timestamp
        db.collection("settings").document("sync_info").set({
            "tasks_last_sync": datetime.now(timezone.utc)
        }, merge=True)

    @staticmethod
    async def get_cached_task(day: int, scenario: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task from the Firestore cache."""
        target_scenario = str(scenario).lower().strip()
        doc_id = f"day_{day}_{target_scenario}"
        doc = db.collection("tasks_matrix").document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
        
        # Fallback to "all" scenario for that day
        doc_id_all = f"day_{day}_all"
        doc_all = db.collection("tasks_matrix").document(doc_id_all).get()
        if doc_all.exists:
            return doc_all.to_dict()
            
        return None

    @staticmethod
    async def save_global_content(key: str, content: Any):
        """Save specialized content (instructions, questions) to cache."""
        db.collection("global_cache").document(key).set({
            "content": content,
            "updated_at": datetime.now(timezone.utc)
        })

    @staticmethod
    async def get_cached_global_content(key: str) -> Optional[Any]:
        """Retrieve specialized content from cache."""
        doc = db.collection("global_cache").document(key).get()
        if doc.exists:
            return doc.to_dict().get("content")
        return None

    @staticmethod
    async def get_sfi_lead(uuid: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific SFI lead result from the web diagnostic in (default) database."""
        # Force use of db_sfi to target (default) database where functions write leads
        doc = db_sfi.collection("sfi_leads").document(uuid).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
