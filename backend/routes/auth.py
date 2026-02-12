"""
Authentication routes: session creation, user info, logout, API keys.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Response, Cookie
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import httpx
import logging

from database import (
    users_collection, sessions_collection, api_keys_collection,
    EMERGENT_AUTH_URL, ALLOWED_DOMAIN,
)
from dependencies import get_current_user, generate_api_key
from models.schemas import SessionCreate, APIKeyCreate
from utils import serialize_doc
from rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/session")
@limiter.limit("10/minute")
async def create_session(request: Request, session_data: SessionCreate, response: Response):
    """Exchange session_id for session_token"""
    try:
        logger.info(f"[AUTH] Received session_id: {session_data.session_id[:20]}...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"[AUTH] Calling Emergent Auth API: {EMERGENT_AUTH_URL}")
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": session_data.session_id}
            )
            logger.info(f"[AUTH] Emergent Auth response status: {auth_response.status_code}")

        if auth_response.status_code != 200:
            logger.info(f"[AUTH] Invalid session_id, status: {auth_response.status_code}")
            raise HTTPException(status_code=401, detail="Invalid session_id")

        user_data = auth_response.json()
        logger.info(f"[AUTH] Got user data: {user_data.get('email')}")

        email = user_data.get("email", "")
        if ALLOWED_DOMAIN and not email.endswith(f"@{ALLOWED_DOMAIN}"):
            logger.info(f"[AUTH] Domain mismatch: {email} vs @{ALLOWED_DOMAIN}")
            raise HTTPException(
                status_code=403,
                detail=f"Access restricted to @{ALLOWED_DOMAIN} emails only"
            )

        logger.info(f"[AUTH] Email verified: {email}")
        session_token = user_data["session_token"]

        user_id = f"user_{uuid.uuid4().hex[:12]}"

        logger.info(f"[AUTH] Upserting user: {email}")
        users_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "name": user_data.get("name", ""),
                    "picture": user_data.get("picture", ""),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "created_at": datetime.now(timezone.utc),
                    "preferences": {"theme": "dark"}
                }
            },
            upsert=True
        )

        logger.info("[AUTH] Fetching user document")
        user_doc = users_collection.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            raise Exception(f"User document not found after upsert: {email}")

        if "user_id" not in user_doc:
            logger.info("[AUTH] Old user detected, adding user_id field")
            new_user_id = f"user_{uuid.uuid4().hex[:12]}"
            users_collection.update_one(
                {"email": email},
                {"$set": {"user_id": new_user_id}}
            )
            user_doc["user_id"] = new_user_id

        actual_user_id = user_doc["user_id"]
        logger.info(f"[AUTH] User ID: {actual_user_id}")

        logger.info("[AUTH] Storing session")
        sessions_collection.update_one(
            {"session_token": session_token},
            {
                "$set": {
                    "user_id": actual_user_id,
                    "session_token": session_token,
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        logger.info("[AUTH] Setting cookie")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,
            path="/"
        )

        logger.info("[AUTH] Success! Returning user data")
        return serialize_doc(user_doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"[AUTH] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user data"""
    return current_user


@router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user and clear session"""
    if session_token:
        sessions_collection.delete_one({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}


@router.post("/auth/api-keys")
@limiter.limit("10/hour")
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Generate a new API key"""
    key, key_hash = generate_api_key()
    key_id = f"key_{uuid.uuid4().hex[:12]}"

    api_key_doc = {
        "key_id": key_id,
        "key_hash": key_hash,
        "key_prefix": key[:12],
        "name": key_data.name,
        "description": key_data.description,
        "created_by": current_user["user_id"],
        "created_by_email": current_user.get("email"),
        "created_at": datetime.now(timezone.utc),
        "last_used_at": None,
        "usage_count": 0,
        "revoked": False
    }

    api_keys_collection.insert_one(api_key_doc)

    return {
        "key_id": key_id,
        "name": key_data.name,
        "key": key,
        "created_at": api_key_doc["created_at"].isoformat(),
        "message": "Save this key securely - it won't be shown again!"
    }


@router.get("/auth/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys for the current user"""
    keys = list(api_keys_collection.find(
        {"created_by": current_user["user_id"], "revoked": {"$ne": True}},
        {"key_hash": 0}
    ))

    return [
        {
            "key_id": k["key_id"],
            "name": k["name"],
            "key_prefix": k.get("key_prefix", "***"),
            "description": k.get("description", ""),
            "created_at": k["created_at"].isoformat() if isinstance(k["created_at"], datetime) else k["created_at"],
            "last_used_at": k["last_used_at"].isoformat() if k.get("last_used_at") else None,
            "usage_count": k.get("usage_count", 0)
        }
        for k in keys
    ]


@router.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke an API key"""
    result = api_keys_collection.update_one(
        {"key_id": key_id, "created_by": current_user["user_id"]},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc)}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked"}
