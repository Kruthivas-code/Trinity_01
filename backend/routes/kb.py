"""
Public Knowledge Base API routes.
Serves articles for the help.emergent.sh-style KB frontend.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from database import db
from dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/kb", tags=["knowledge_base_public"])

kb_articles = db["kb_articles"]
kb_navigation = db["kb_navigation"]
kb_image_files = db["kb_image_files"]
kb_feedback = db["kb_feedback"]


# ── Image serving ─────────────────────────────────────────────

@router.get("/images/{filename}")
async def get_kb_image(filename: str):
    """Serve KB images from MongoDB."""
    doc = kb_image_files.find_one({"filename": filename}, {"_id": 0})
    if not doc or "data" not in doc:
        raise HTTPException(404, detail="Image not found")
    return Response(
        content=doc["data"],
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


# ── Public endpoints ──────────────────────────────────────────

@router.get("/navigation")
async def get_navigation():
    nav = kb_navigation.find_one({}, {"_id": 0})
    if not nav:
        return {"nav_groups": []}
    return {"nav_groups": nav.get("nav_groups", [])}


# Icon mapping for nav groups
NAV_GROUP_ICONS = {
    "beginners-guide": "book-open",
    "features": "zap",
    "building-your-app": "code",
    "deploy-and-manage": "rocket",
    "troubleshooting": "wrench",
}


@router.get("/public-data")
async def get_public_data():
    """Serve KB data in the format expected by the PublicDocs frontend (mirrors help.emergent.sh API)."""
    nav_doc = kb_navigation.find_one({}, {"_id": 0})
    nav_groups = (nav_doc or {}).get("nav_groups", [])

    all_articles = list(kb_articles.find({"published": True}, {"_id": 0}).sort("order", 1))

    # Build navigation tabs from nav_groups
    tabs = []
    for group in nav_groups:
        tab_groups = []
        for section in group.get("sections", []):
            section_articles = [
                a for a in all_articles
                if a.get("nav_group_key") == group["key"] and a.get("section_key") == section["key"]
            ]
            pages = [{"page": a["slug"], "title": a["title"], "icon": a.get("icon", "")} for a in section_articles]
            if pages:
                tab_groups.append({"group": section.get("label", section["key"]), "pages": pages})
        tabs.append({
            "id": group["key"],
            "label": group.get("label", group["key"]),
            "icon": group.get("icon") or NAV_GROUP_ICONS.get(group["key"], "file-text"),
            "groups": tab_groups,
        })

    # Build documents list
    documents = []
    for a in all_articles:
        documents.append({
            "id": a["slug"],
            "slug": a["slug"],
            "title": a["title"],
            "content": a.get("content_markdown", ""),
            "order": a.get("order", 0),
            "icon": None,
        })

    project = {"id": "trinity-kb", "name": "Emergent", "slug": "emergent"}
    config = {
        "site_title": "Emergent Docs",
        "site_description": "Documentation and guides for building with Emergent",
        "navbar": {
            "links": [{"label": "Help", "href": "/portal"}],
            "primary": {"label": "Try Emergent", "href": "https://app.emergent.sh"},
        },
        "navigation": {"tabs": tabs},
    }

    return {"project": project, "config": config, "documents": documents}


@router.get("/articles")
async def list_articles(nav_group: Optional[str] = None, section: Optional[str] = None):
    query = {"published": True}
    if nav_group:
        query["nav_group_key"] = nav_group
    if section:
        query["section_key"] = section
    articles = list(kb_articles.find(query, {"_id": 0, "content_markdown": 0}).sort("order", 1))
    return {"articles": articles}


@router.get("/articles/{slug}")
async def get_article(slug: str):
    article = kb_articles.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    # Get prev/next for navigation
    order = article.get("order", 0)
    prev_art = kb_articles.find_one(
        {"published": True, "order": {"$lt": order}},
        {"_id": 0, "slug": 1, "title": 1},
        sort=[("order", -1)]
    )
    next_art = kb_articles.find_one(
        {"published": True, "order": {"$gt": order}},
        {"_id": 0, "slug": 1, "title": 1},
        sort=[("order", 1)]
    )
    return {
        "article": article,
        "prev": prev_art,
        "next": next_art,
    }


# ── Feedback ───────────────────────────────────────────────────

class FeedbackBody(BaseModel):
    helpful: bool

@router.post("/articles/{slug}/feedback")
async def submit_feedback(slug: str, body: FeedbackBody):
    article = kb_articles.find_one({"slug": slug, "published": True})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    kb_feedback.insert_one({
        "article_slug": slug,
        "helpful": body.helpful,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok"}

@router.get("/articles/{slug}/feedback")
async def get_article_feedback(slug: str):
    pipeline = [
        {"$match": {"article_slug": slug}},
        {"$group": {"_id": None, "total": {"$sum": 1}, "helpful": {"$sum": {"$cond": ["$helpful", 1, 0]}}}},
    ]
    result = list(kb_feedback.aggregate(pipeline))
    if not result:
        return {"total": 0, "helpful": 0, "unhelpful": 0}
    r = result[0]
    return {"total": r["total"], "helpful": r["helpful"], "unhelpful": r["total"] - r["helpful"]}


@router.get("/search")
async def search_articles(q: str = ""):
    if not q or len(q) < 2:
        return {"results": []}
    regex = {"$regex": q, "$options": "i"}
    results = list(kb_articles.find(
        {"published": True, "$or": [{"title": regex}, {"content_markdown": regex}]},
        {"_id": 0, "content_markdown": 0}
    ).sort("order", 1).limit(20))
    return {"results": results}


# ── Admin endpoints ───────────────────────────────────────────

@router.get("/admin/articles")
async def admin_list_articles(current_user: dict = Depends(get_current_user)):
    articles = list(kb_articles.find({}, {"_id": 0}).sort("order", 1))
    nav = kb_navigation.find_one({}, {"_id": 0})
    # Attach feedback stats per article
    feedback_pipeline = [
        {"$group": {"_id": "$article_slug", "total": {"$sum": 1}, "helpful": {"$sum": {"$cond": ["$helpful", 1, 0]}}}},
    ]
    stats = {r["_id"]: {"total": r["total"], "helpful": r["helpful"]} for r in kb_feedback.aggregate(feedback_pipeline)}
    for a in articles:
        s = stats.get(a["slug"], {"total": 0, "helpful": 0})
        a["feedback_total"] = s["total"]
        a["feedback_helpful"] = s["helpful"]
    return {"articles": articles, "nav_groups": (nav or {}).get("nav_groups", [])}


@router.put("/admin/navigation")
async def update_navigation(body: dict, current_user: dict = Depends(get_current_user)):
    nav_groups = body.get("nav_groups", [])
    kb_navigation.update_one({}, {"$set": {"nav_groups": nav_groups, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"nav_groups": nav_groups}


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    section_key: Optional[str] = None
    section_label: Optional[str] = None
    nav_group_key: Optional[str] = None
    nav_group_label: Optional[str] = None
    content_markdown: Optional[str] = None
    published: Optional[bool] = None
    order: Optional[int] = None
    icon: Optional[str] = None


class ArticleCreate(BaseModel):
    title: str
    slug: str
    section_key: str
    section_label: str
    nav_group_key: str
    nav_group_label: str
    content_markdown: str = ""
    published: bool = True
    order: int = 0
    icon: str = ""


@router.post("/admin/articles")
async def create_article(body: ArticleCreate, current_user: dict = Depends(get_current_user)):
    existing = kb_articles.find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    doc = body.dict()
    # Auto-set order if 0: place at end of the target section
    if doc.get("order", 0) == 0:
        last = kb_articles.find_one(
            {"nav_group_key": doc["nav_group_key"], "section_key": doc["section_key"]},
            sort=[("order", -1)]
        )
        if last:
            doc["order"] = last.get("order", 0) + 1
        else:
            # New section — find the max global order and add 1
            max_doc = kb_articles.find_one({}, sort=[("order", -1)])
            doc["order"] = (max_doc.get("order", 0) + 1) if max_doc else 0
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    kb_articles.insert_one(doc)
    # Auto-sync navigation: ensure nav group and section exist
    nav_doc = kb_navigation.find_one({})
    if nav_doc:
        nav_groups = nav_doc.get("nav_groups", [])
        group = next((g for g in nav_groups if g["key"] == doc["nav_group_key"]), None)
        if not group:
            nav_groups.append({"key": doc["nav_group_key"], "label": doc["nav_group_label"], "sections": [{"key": doc["section_key"], "label": doc["section_label"]}]})
            kb_navigation.update_one({}, {"$set": {"nav_groups": nav_groups}})
        else:
            sec = next((s for s in group.get("sections", []) if s["key"] == doc["section_key"]), None)
            if not sec:
                group.setdefault("sections", []).append({"key": doc["section_key"], "label": doc["section_label"]})
                kb_navigation.update_one({}, {"$set": {"nav_groups": nav_groups}})
    return kb_articles.find_one({"slug": body.slug}, {"_id": 0})


@router.put("/admin/articles/{slug}")
async def update_article(slug: str, body: ArticleUpdate, current_user: dict = Depends(get_current_user)):
    article = kb_articles.find_one({"slug": slug})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    updates = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    if "slug" in updates and updates["slug"] != slug:
        conflict = kb_articles.find_one({"slug": updates["slug"]})
        if conflict:
            raise HTTPException(status_code=409, detail="Slug already in use")
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        kb_articles.update_one({"slug": slug}, {"$set": updates})
    final_slug = updates.get("slug", slug)
    return kb_articles.find_one({"slug": final_slug}, {"_id": 0})


@router.delete("/admin/articles/{slug}")
async def delete_article(slug: str, current_user: dict = Depends(get_current_user)):
    result = kb_articles.delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Deleted"}


# ── Admin image upload ────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/avif", "image/svg+xml"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/admin/images")
async def upload_kb_image(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload an image for use in KB articles. Stores in MongoDB."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, detail=f"Unsupported file type: {file.content_type}. Allowed: png, jpg, gif, webp, avif, svg")

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, detail="File too large. Maximum size is 10 MB.")

    # Generate a unique filename preserving extension
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "png"
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"

    kb_image_files.insert_one({
        "filename": unique_name,
        "original_name": file.filename,
        "content_type": file.content_type,
        "data": data,
        "size": len(data),
        "uploaded_at": datetime.now(timezone.utc),
        "uploaded_by": current_user.get("email", "unknown"),
    })

    return {"filename": unique_name, "url": f"/api/kb/images/{unique_name}", "size": len(data)}


@router.get("/admin/images")
async def list_kb_images(current_user: dict = Depends(get_current_user)):
    """List all uploaded KB images (without binary data)."""
    images = list(kb_image_files.find({}, {"_id": 0, "data": 0}).sort("uploaded_at", -1).limit(100))
    return {"images": images}


@router.delete("/admin/images/{filename}")
async def delete_kb_image(filename: str, current_user: dict = Depends(get_current_user)):
    result = kb_image_files.delete_one({"filename": filename})
    if result.deleted_count == 0:
        raise HTTPException(404, detail="Image not found")
    return {"message": "Deleted"}



# ── Bulk move articles between nav groups/sections ────────────

class BulkMoveRequest(BaseModel):
    source_group_key: str
    source_section_key: str
    target_group_key: str
    target_group_label: str
    target_section_key: str
    target_section_label: str


@router.post("/admin/articles/bulk-move")
async def bulk_move_articles(body: BulkMoveRequest, current_user: dict = Depends(get_current_user)):
    """Move all articles from one section to another group/section."""
    result = kb_articles.update_many(
        {"nav_group_key": body.source_group_key, "section_key": body.source_section_key},
        {"$set": {
            "nav_group_key": body.target_group_key,
            "nav_group_label": body.target_group_label,
            "section_key": body.target_section_key,
            "section_label": body.target_section_label,
            "updated_at": datetime.now(timezone.utc),
        }}
    )
    return {"moved": result.modified_count}