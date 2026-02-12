"""
Auth dependencies and role-based authorization for FastAPI routes.
"""
from fastapi import HTTPException, Depends, Request, Cookie, Security
from fastapi.security import APIKeyHeader
from typing import Optional, List
from datetime import datetime, timezone
import hashlib

from database import (
    users_collection, sessions_collection, api_keys_collection,
    VALID_ROLES,
)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str) -> Optional[dict]:
    """Verify an API key and return the key document if valid"""
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    api_key_doc = api_keys_collection.find_one({"key_hash": key_hash}, {"_id": 0})
    if api_key_doc and api_key_doc.get("is_active", True):
        api_keys_collection.update_one(
            {"key_hash": key_hash},
            {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}}
        )
        return api_key_doc
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
