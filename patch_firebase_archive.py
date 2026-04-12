
import sys
import os

def patch_firebase_db():
    filepath = r'c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\database\firebase_db.py'
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_code = """    @staticmethod
    async def get_archived_users() -> List[Dict[str, Any]]:
        \"\"\"Get all archived users (Sync wrapper).\"\"\"
        query = db.collection("users").where("status", "==", "archived")
        docs = query.stream()
        users = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            users.append(d)
        return users"""

    new_code = """    @staticmethod
    async def get_archived_users(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        \"\"\"Get archived users with pagination (Sync wrapper).\"\"\"
        query = db.collection("users").where("status", "==", "archived").limit(limit+offset)
        docs = list(query.stream())
        # Manual offset because sync Firestore stream doesn't support offset easily
        users = []
        for doc in docs[offset:]:
            d = doc.to_dict()
            d['id'] = doc.id
            users.append(d)
        return users"""

    if old_code in content:
        new_content = content.replace(old_code, new_code)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully patched get_archived_users in firebase_db.py")
    else:
        print("Could not find get_archived_users in firebase_db.py")

if __name__ == "__main__":
    patch_firebase_db()
