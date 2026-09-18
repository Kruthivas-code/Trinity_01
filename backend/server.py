"""
Trinity Docs Platform API
Main application entry point. All routes are in backend/routes/.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime, timezone
import logging
import uuid
import os

from database import db, client, MONGO_URL
from rate_limiter import limiter

# ==================== Logging ====================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', '-')
        return True

for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())

# ==================== Environment Validation ====================
def validate_environment():
    required_vars = ["MONGO_URL"]
    recommended_vars = ["ALLOWED_ORIGINS"]
    missing_required = [v for v in required_vars if not os.environ.get(v)]
    missing_recommended = [v for v in recommended_vars if not os.environ.get(v)]
    if missing_required:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_required)}")
    if missing_recommended:
        logger.warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")

validate_environment()

# ==================== App Creation ====================
tags_metadata = [
    {"name": "auth", "description": "Authentication, sessions, and API key management"},
    {"name": "knowledge_base_public", "description": "Public documentation content, navigation, search, and feedback"},
    {"name": "kb_review", "description": "Review-mode workflow: assignments, comments, verdicts, activity, and publish gating"},
    {"name": "health", "description": "System health checks"},
]

app = FastAPI(
    title="Trinity Docs Platform API",
    description="Public documentation viewer, content editor, and review workflow.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ==================== Include All Route Modules ====================
from routes.auth import router as auth_router
from routes.kb import router as kb_router, seed_kb_articles, migrate_flat_nav_to_tree
from routes.review import router as review_router

app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(review_router)

# ==================== Middleware ====================
MAX_REQUEST_BODY_SIZE = 50 * 1024 * 1024  # 50MB

@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_SIZE:
        return JSONResponse(status_code=413, content={"detail": "Request body too large. Maximum size is 50MB."})
    return await call_next(request)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.error(f"Unhandled exception: {str(exc)}", extra={"request_id": request_id}, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred", "request_id": request_id}
    )

# CORS
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    ALLOWED_ORIGINS = [
        "https://repo-builder-83.preview.emergentagent.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

# When a wildcard is configured we CANNOT use a literal "*" together with
# allow_credentials=True — browsers reject a credentialed request whose
# Access-Control-Allow-Origin is "*", which silently drops the auth cookie
# and bounces the user back to /login. Instead, use allow_origin_regex so the
# middleware reflects the exact request origin (a valid value for credentials).
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-API-Key", "X-Session-ID"],
}
if "*" in ALLOWED_ORIGINS:
    cors_kwargs["allow_origin_regex"] = ".*"
    cors_kwargs["allow_origins"] = []
else:
    cors_kwargs["allow_origins"] = ALLOWED_ORIGINS

app.add_middleware(CORSMiddleware, **cors_kwargs)

# ==================== Health Check ====================
@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
async def health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    try:
        client.admin.command('ping')
        health_status["checks"]["database"] = {"status": "healthy", "type": "mongodb"}
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "type": "mongodb", "error": "Connection failed"}
        logger.error(f"Health check database error: {e}")
    try:
        collections = db.list_collection_names()
        required = ["users", "kb_articles"]
        missing = [c for c in required if c not in collections]
        health_status["checks"]["collections"] = {"status": "healthy" if not missing else "warning", "missing": missing or None}
    except Exception as e:
        health_status["checks"]["collections"] = {"status": "error", "error": "Check failed"}
        logger.error(f"Health check collections error: {e}")
    if health_status["status"] == "unhealthy":
        return JSONResponse(status_code=503, content=health_status)
    return health_status


# ==================== Startup / Shutdown ====================
@app.on_event("startup")
async def startup_event():
    seed_kb_articles()
    migrate_flat_nav_to_tree()
    logger.info("[STARTUP] Trinity Docs Platform started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
