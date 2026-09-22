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

# AI Writing Assistant (Phase 3): Universal LLM key for emergentintegrations'
# LlmChat, same "read once here, import the constant everywhere else" pattern
# as COOKIE_DOMAIN below. Empty string (not None) when unset, matching how
# help-doc-v3's server.py reads it -- routes/assistant.py treats "" as "not
# configured" and 503s rather than crashing on every request.
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Image Picker (Phase 4): Unsplash stock-photo search proxy. Defaults to the
# literal string "demo" (Unsplash's own public demo Client-ID, rate-limited
# but functional) when unset -- matching help-doc-v3's server.py exactly, so
# the stock tab works out of the box in dev without any env var configured.
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "demo")

# Session cookie domain. The preview/prod infra 307-redirects /api/* to a
# sibling subdomain (e.g. *.internal.preview.emergentagent.com), so a
# host-only cookie set on the internal host is NOT sent back to the main
# host on subsequent requests -> auth appears lost -> login redirect loop.
# Setting the shared parent domain (with leading dot) makes the cookie valid
# across both subdomains. Leave unset (None) for local dev so the cookie
# stays host-only. Configured via COOKIE_DOMAIN env var, never hardcoded.
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN") or None
