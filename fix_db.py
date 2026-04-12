import codecs
import os
FILE_PATH = r"c:\Sher_AI_Studio\projects\Shadow_Corp\Sprint_bot\database\firebase_db.py"
target = """    @staticmethod
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
replacement = """    @staticmethod
    async def get_archived_users(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        \"\"\"Get archived users with pagination (Sync wrapper).\"\"\"
        query = db.collection("users").where("status", "==", "archived").limit(limit + offset)
        docs = list(query.stream())
        users = []
        subset = docs[offset:] if len(docs) > offset else []
        for doc in subset:
            d = doc.to_dict()
            d['id'] = doc.id
            users.append(d)
        return users"""
with codecs.open(FILE_PATH, "r", "utf-8") as f:
    content = f.read()
if target in content:
    content = content.replace(target, replacement)
    with codecs.open(FILE_PATH, "w", "utf-8") as f:
        f.write(content)
    print("SUCCESS")
else:
    print("FAILED")
