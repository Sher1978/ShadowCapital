import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys

# Create mock for firebase_admin
mock_firebase_admin = MagicMock()
mock_firebase_admin._apps = True # Pretend it's already initialized
sys.modules["firebase_admin"] = mock_firebase_admin

# Create mock for firestore
mock_firestore = MagicMock()
mock_client = MagicMock()
mock_firestore.client.return_value = mock_client
sys.modules["firebase_admin.firestore"] = mock_firestore

import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now we can import things that use firebase_admin
from database.firebase_db import FirestoreDB
FirestoreDB.get_user = AsyncMock()
FirestoreDB.create_user = AsyncMock()

# Mock bot and other utils if necessary
import bot.handlers.client as client_handlers

async def test_activate_request_handler_new_user():
    print("Testing activate_request_handler for a NEW user...")
    
    # Setup mocks
    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    mock_message.from_user.full_name = "Test User"
    mock_message.from_user.username = "testuser"
    
    # Simulate user doesn't exist yet or is "new"
    FirestoreDB.get_user.return_value = {
        "id": "doc_123",
        "status": "new",
        "tg_id": 12345
    }
    
    # Call the handler
    await client_handlers.activate_request_handler(mock_message)
    
    # Verify results
    # It should have called message.answer with the rules text
    args, kwargs = mock_message.answer.call_args
    text = args[0]
    reply_markup = kwargs.get('reply_markup')
    
    print(f"Message sent: {text[:50]}...")
    assert "Перед активацией твоего профиля" in text
    assert reply_markup is not None
    print("✅ Success: Rules message sent to NEW user.")

async def test_activate_request_handler_pending_user():
    print("\nTesting activate_request_handler for a PENDING user...")
    
    # Setup mocks
    mock_message = AsyncMock()
    mock_message.from_user.id = 12345
    
    # Simulate user is "pending"
    FirestoreDB.get_user.return_value = {
        "id": "doc_123",
        "status": "pending",
        "tg_id": 12345
    }
    
    # Call the handler
    await client_handlers.activate_request_handler(mock_message)
    
    # Verify results
    # It should have called message.answer with the "pending" message
    args, kwargs = mock_message.answer.call_args
    text = args[0]
    
    print(f"Message sent: {text}")
    assert "Твоя заявка на рассмотрении" in text
    print("✅ Success: Pending message sent to PENDING user.")

if __name__ == "__main__":
    asyncio.run(test_activate_request_handler_new_user())
    asyncio.run(test_activate_request_handler_pending_user())
