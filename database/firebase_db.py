import firebase_admin
from firebase_admin import credentials
from google.cloud.firestore import AsyncClient, Query
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Initialize Firebase Admin SDK (still needed for some metadata/auth if used)
if not firebase_admin._apps:
    try:
        cred_path = "credentials.json"
        res_cred_path = os.path.join("resources", "google_credentials.json")
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logging.info("✅ Firebase Admin initialized with credentials.json")
        elif os.path.exists(res_cred_path):
            cred = credentials.Certificate(res_cred_path)
            firebase_admin.initialize_app(cred)
            logging.info(f"✅ Firebase Admin initialized with {res_cred_path}")
        else:
            firebase_admin.initialize_app()
            logging.info("✅ Firebase Admin initialized with Application Default Credentials")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Firebase Admin: {e}")

# Use AsyncClient for non-blocking Firestore operations
database_id = os.getenv("FIREBASE_DATABASE_ID", "(default)")
db = AsyncClient(database=database_id)
logging.info(f"🔥 Async Firestore client created for database: {database_id}")

class FirestoreDB:
    db = db  # Expose the async client
    
    @staticmethod
    async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user by Telegram ID (Async)."""
        query = db.collection("users").where("tg_id", "==", tg_id).limit(1)
        docs = query.stream()
        async for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> str:
        """Create a new user document (Async)."""
        user_data['created_at'] = datetime.now(timezone.utc)
        doc_ref = await db.collection("users").add(user_data)
        # add returns (time, reference)
        return doc_ref[1].id

    @staticmethod
    async def update_user(doc_id: str, update_data: Dict[str, Any]):
        """Update user fields (Async)."""
        await db.collection("users").document(doc_id).update(update_data)

    @staticmethod
    async def add_log(user_doc_id: str, log_data: Dict[str, Any]):
        """Add a shadow log for a user (Async)."""
        log_data['created_at'] = datetime.now(timezone.utc)
        await db.collection("users").document(user_doc_id).collection("logs").add(log_data)

    @staticmethod
    async def get_logs(user_doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs for a user (Async)."""
        query = db.collection("users").document(user_doc_id).collection("logs") \
                  .order_by("created_at", direction=Query.DESCENDING) \
                  .limit(limit)
        docs = query.stream()
        return [doc.to_dict() async for doc in docs]

    @staticmethod
    async def get_today_log(user_doc_id: str) -> Optional[Dict[str, Any]]:
        """Check if there's a log for the current UTC day (Async)."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        query = db.collection("users").document(user_doc_id).collection("logs") \
                  .where("created_at", ">=", today_start) \
                  .limit(1)
        docs = query.stream()
        async for doc in docs:
            return doc.to_dict()
        return None

    @staticmethod
    async def get_global_settings() -> Dict[str, Any]:
        """Fetch global settings (Async)."""
        doc = await db.collection("settings").document("global").get()
        if doc.exists:
            return doc.to_dict()
        else:
            # Default settings
            defaults = {
                "morning_time": "09:00",
                "deadline_time": "20:30",
                "evening_time": "21:30",
                "sunday_time": "18:00"
            }
            await db.collection("settings").document("global").set(defaults)
            return defaults

    @staticmethod
    async def update_global_settings(update_data: Dict[str, Any]):
        """Update global settings (Async)."""
        await db.collection("settings").document("global").update(update_data)

    @staticmethod
    async def get_active_users() -> List[Dict[str, Any]]:
        """Get all active users for scheduler (Async)."""
        query = db.collection("users").where("status", "==", "active")
        docs = query.stream()
        return [doc.to_dict() async for doc in docs]

    @staticmethod
    async def delete_user_and_data(tg_id: int):
        """Recursively delete user and all their logs (Async)."""
        query = db.collection("users").where("tg_id", "==", tg_id).limit(1)
        docs = query.stream()
        async for doc in docs:
            # Delete all logs in subcollection
            logs = db.collection("users").document(doc.id).collection("logs").stream()
            async for log in logs:
                await db.collection("users").document(doc.id).collection("logs").document(log.id).delete()
            # Delete user document
            await db.collection("users").document(doc.id).delete()
            logging.info(f"🗑 Deleted user {tg_id} and all related logs.")
