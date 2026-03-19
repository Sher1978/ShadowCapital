import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Initialize Firebase Admin SDK
# In Cloud Run, it will automatically use the default service account.
# Locally, you'll need GOOGLE_APPLICATION_CREDENTIALS env var.
if not firebase_admin._apps:
    try:
        # Check for local credentials file, otherwise rely on default service account
        # Use credentials.json if present, otherwise rely on environment (ADC or default account)
        cred_path = "credentials.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            # On Cloud Run, this will use the default service account of the current project
            firebase_admin.initialize_app(options={
                'projectId': 'shershadow' # Explicitly set project ID
            })
        logging.info("🔥 Firebase Admin initialized successfully")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Firebase Admin: {e}")

# Используем конкретный ID базы данных, так как (default) в этом проекте недоступен
db = firestore.client(database_id="test-db-123456789")

class FirestoreDB:
    db = db  # Expose the firestore client for direct access
    
    @staticmethod
    async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user by Telegram ID."""
        docs = db.collection("users").where("tg_id", "==", tg_id).limit(1).stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> str:
        """Create a new user document."""
        user_data['created_at'] = datetime.now(timezone.utc)
        _, doc_ref = db.collection("users").add(user_data)
        return doc_ref.id

    @staticmethod
    async def update_user(doc_id: str, update_data: Dict[str, Any]):
        """Update user fields."""
        db.collection("users").document(doc_id).update(update_data)

    @staticmethod
    async def add_log(user_doc_id: str, log_data: Dict[str, Any]):
        """Add a shadow log for a user."""
        log_data['created_at'] = datetime.now(timezone.utc)
        db.collection("users").document(user_doc_id).collection("logs").add(log_data)

    @staticmethod
    async def get_logs(user_doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs for a user."""
        docs = db.collection("users").document(user_doc_id).collection("logs") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [doc.to_dict() for doc in docs]

    @staticmethod
    async def get_global_settings() -> Dict[str, Any]:
        """Fetch global settings."""
        doc = db.collection("settings").document("global").get()
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
            db.collection("settings").document("global").set(defaults)
            return defaults

    @staticmethod
    async def update_global_settings(update_data: Dict[str, Any]):
        """Update global settings."""
        db.collection("settings").document("global").update(update_data)

    @staticmethod
    async def get_active_users() -> List[Dict[str, Any]]:
        """Get all active users for scheduler."""
        docs = db.collection("users").where("status", "==", "active").stream()
        return [doc.to_dict() for doc in docs]
    @staticmethod
    async def delete_user_and_data(tg_id: int):
        """Recursively delete user and all their logs."""
        docs = db.collection("users").where("tg_id", "==", tg_id).limit(1).stream()
        for doc in docs:
            # Delete all logs in subcollection
            logs = db.collection("users").document(doc.id).collection("logs").stream()
            for log in logs:
                db.collection("users").document(doc.id).collection("logs").document(log.id).delete()
            # Delete user document
            db.collection("users").document(doc.id).delete()
            logging.info(f"🗑 Deleted user {tg_id} and all related logs.")
