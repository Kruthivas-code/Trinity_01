"""
Database connection and collection references.
All MongoDB collections are defined here as the single source of truth.
"""
import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("server")

# MongoDB Connection
MONGO_URL = os.environ.get("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client[os.environ.get("DB_NAME")]

# Core collections
users_collection = db.users
sessions_collection = db.user_sessions
api_keys_collection = db.api_keys

# ==================== Constants ====================

# Role-based auth
VALID_ROLES = ["agent", "lead", "admin"]

# Emergent Auth
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ALLOWED_DOMAIN = None

# Session cookie domain. The preview/prod infra 307-redirects /api/* to a
# sibling subdomain (e.g. *.internal.preview.emergentagent.com), so a
# host-only cookie set on the internal host is NOT sent back to the main
# host on subsequent requests -> auth appears lost -> login redirect loop.
# Setting the shared parent domain (with leading dot) makes the cookie valid
# across both subdomains. Leave unset (None) for local dev so the cookie
# stays host-only. Configured via COOKIE_DOMAIN env var, never hardcoded.
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None
