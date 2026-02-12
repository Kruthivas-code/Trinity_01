"""
Rate limiter shared instance - imported by routes that need per-endpoint rate limiting.
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from database import MONGO_URL

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],
    strategy="fixed-window",
    storage_uri=MONGO_URL,
    storage_options={"database_name": os.environ.get("DB_NAME")}
)
