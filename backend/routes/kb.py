"""
Public Knowledge Base API routes.
Serves articles for the help.emergent.sh-style KB frontend.
"""
from fastapi import APIRouter, HTTPException, Depends
from database import db
from dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/kb", tags=["knowledge_base_public"])

kb_articles = db["kb_articles"]
kb_navigation = db["kb_navigation"]


# ── Public endpoints ──────────────────────────────────────────

@router.get("/navigation")
async def get_navigation():
    nav = kb_navigation.find_one({}, {"_id": 0})
    if not nav:
        return {"nav_groups": []}
    return {"nav_groups": nav.get("nav_groups", [])}


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
    section_key = article.get("section_key")
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


@router.post("/admin/articles")
async def create_article(body: ArticleCreate, current_user: dict = Depends(get_current_user)):
    existing = kb_articles.find_one({"slug": body.slug})
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    doc = body.dict()
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    kb_articles.insert_one(doc)
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
