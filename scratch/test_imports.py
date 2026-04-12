print("Trying to import routers...")
from bot.handlers.client import client_router
print("Client router loaded.")
from bot.handlers.admin import admin_router
print("Admin router loaded.")
from bot.handlers.audit import audit_router
print("Audit router loaded.")
print("All routers loaded successfully.")
