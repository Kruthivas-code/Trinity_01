"""
Auth dependencies and role-based authorization for FastAPI routes.
"""
from fastapi import HTTPException, Depends, Request, Cookie, Security
from fastapi.security import APIKeyHeader
from typing import Optional, List
from datetime import datetime, timezone
import secrets
import hashlib
import bcrypt

from database import (
    users_collection, sessions_collection, api_keys_collection,
    VALID_ROLES,
)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> tuple:
    """Generate API key, its bcrypt hash, and a SHA-256 hash for fast lookup"""
    key = f"tk_live_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    key_sha256 = hashlib.sha256(key.encode('utf-8')).hexdigest()
    return key, key_hash, key_sha256


def verify_api_key(key: str) -> Optional[dict]:
    """Verify API key using SHA-256 indexed lookup + bcrypt verification"""
    if not key:
        return None
    key_sha256 = hashlib.sha256(key.encode('utf-8')).hexdigest()
    api_key_doc = api_keys_collection.find_one({"key_sha256": key_sha256, "revoked": {"$ne": True}})
    if api_key_doc:
        stored_hash = api_key_doc.get("key_hash", "")
        try:
            if bcrypt.checkpw(key.encode('utf-8'), stored_hash.encode('utf-8')):
                api_keys_collection.update_one(
                    {"_id": api_key_doc["_id"]},
                    {"$set": {"last_used_at": datetime.now(timezone.utc)}, "$inc": {"usage_count": 1}}
                )
                return api_key_doc
        except (ValueError, TypeError):
            pass
    # Fallback: scan for keys without key_sha256 (migration support)
    legacy_keys = list(api_keys_collection.find({"revoked": {"$ne": True}, "key_sha256": {"$exists": False}}))
    for legacy_doc in legacy_keys:
        stored_hash = legacy_doc.get("key_hash", "")
        try:
            if bcrypt.checkpw(key.encode('utf-8'), stored_hash.encode('utf-8')):
                api_keys_collection.update_one(
                    {"_id": legacy_doc["_id"]},
                    {"$set": {"last_used_at": datetime.now(timezone.utc), "key_sha256": key_sha256}, "$inc": {"usage_count": 1}}
                )
                return legacy_doc
        except (ValueError, TypeError):
            continue
    return None


async def get_api_key_user(api_key: str = Security(API_KEY_HEADER)) -> Optional[dict]:
    """Authenticate via API key - returns None if no key provided"""
    if not api_key:
        return None
    api_key_doc = verify_api_key(api_key)
    if api_key_doc:
        return {
            "user_id": api_key_doc.get("created_by", "api"),
            "email": api_key_doc.get("created_by_email", "api@system"),
            "name": api_key_doc.get("name", "API Key"),
            "auth_type": "api_key",
            "api_key_id": api_key_doc.get("key_id")
        }
    return None


def _serialize_user(doc):
    """Minimal serialization for user docs returned by auth."""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            continue
        elif hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    if "user_id" in result and "id" not in result:
        result["id"] = result["user_id"]
    return result


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    api_key: str = Security(API_KEY_HEADER)
):
    """Get current user from session token or API key"""
    if api_key:
        api_user = await get_api_key_user(api_key)
        if api_user:
            return api_user
        raise HTTPException(status_code=401, detail="Invalid API key")

    token = session_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = sessions_collection.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        sessions_collection.delete_one({"session_token": token})
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = users_collection.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    return _serialize_user(user_doc)


def require_role(allowed_roles: List[str]):
    """Dependency that checks if the current user has one of the allowed roles."""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "agent")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency that requires admin role"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


def require_lead_or_admin(current_user: dict = Depends(get_current_user)):
    """Dependency that requires lead or admin role"""
    if current_user.get("role") not in ["admin", "lead"]:
        raise HTTPException(status_code=403, detail="Lead or admin privileges required")
    return current_user
