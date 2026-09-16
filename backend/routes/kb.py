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
import os
import uuid
import logging
import requests
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge_base_public"])

kb_articles = db["kb_articles"]
kb_navigation = db["kb_navigation"]
kb_image_files = db["kb_image_files"]
kb_feedback = db["kb_feedback"]
kb_settings = db["kb_settings"]

KB_SOURCE_API = "https://help.emergent.sh/api/public/default-project"


def seed_kb_articles():
    """Seed KB articles from help.emergent.sh if the collection is empty.
    Called on server startup — idempotent, only runs on fresh databases."""
    if kb_articles.count_documents({}) > 0:
        return

    logger.info("[KB] kb_articles is empty — seeding from help.emergent.sh...")
    try:
        resp = requests.get(KB_SOURCE_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"[KB] Failed to fetch from help.emergent.sh: {e}")
        return

    documents = data.get("documents", [])
    config = data.get("config", {})
    tabs = config.get("navigation", {}).get("tabs", [])

    doc_map = {doc["slug"]: doc for doc in documents if doc.get("slug")}

    # Build nav_groups for kb_navigation
    nav_groups = []
    for tab in tabs:
        sections = []
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            pages = group.get("pages", [])
            page_slugs = [p.get("page") if isinstance(p, dict) else p for p in pages]
            sections.append({"key": section_key, "label": group["group"], "articles": page_slugs})
        nav_groups.append({
            "key": tab["id"],
            "label": tab.get("label", tab["id"]),
            "icon": tab.get("icon", "file-text"),
            "sections": sections,
        })

    # Insert articles with full metadata
    order = 0
    inserted = 0
    for tab in tabs:
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            for page in group.get("pages", []):
                slug = page.get("page") if isinstance(page, dict) else page
                doc = doc_map.get(slug)
                if not doc:
                    continue

                content = doc.get("content", "")
                title = doc.get("title") or (page.get("title") if isinstance(page, dict) else slug)
                icon = (page.get("icon", "") if isinstance(page, dict) else "") or doc.get("icon", "")

                # Generate description from first ~160 chars of plain content
                desc_text = content.replace("#", "").replace(">", "").replace("*", "").strip()
                desc_lines = [l.strip() for l in desc_text.split("\n") if l.strip() and not l.strip().startswith("<")]
                description = (desc_lines[0][:160] + "...") if desc_lines and len(desc_lines[0]) > 160 else (desc_lines[0] if desc_lines else "")

                article = {
                    "slug": slug,
                    "title": title,
                    "description": description,
                    "content_markdown": content,
                    "nav_group_key": tab["id"],
                    "nav_group_label": tab.get("label", tab["id"]),
                    "section_key": section_key,
                    "section_label": group["group"],
                    "icon": icon,
                    "order": order,
                    "published": True,
                    "source_url": f"https://help.emergent.sh/{slug}",
                    "created_at": _parse_api_date(doc.get("created_at")),
                    "updated_at": _parse_api_date(doc.get("updated_at")),
                }
                kb_articles.insert_one(article)
                inserted += 1
                order += 1

    # Update navigation
    kb_navigation.delete_many({})
    kb_navigation.insert_one({"nav_groups": nav_groups})

    logger.info(f"[KB] Seeded {inserted} articles and {len(nav_groups)} nav groups from help.emergent.sh")


def _parse_api_date(val) -> datetime:
    """Parse a date string from the API, falling back to now()."""
    if not val:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


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

    # Public, unauthenticated flag for the optional horizontal tab switcher on
    # the docs nav. Defaults to False (today's stacked behavior) when unset.
    docs_settings_doc = kb_settings.find_one({"type": "docs_settings"}, {"_id": 0, "tabs_enabled": 1})
    tabs_enabled = bool((docs_settings_doc or {}).get("tabs_enabled", False))

    # Build navigation tabs from nav_groups
    tabs = []
    for group in nav_groups:
        # Skip hidden categories
        if group.get("published") is False:
            continue
        tab_groups = []
        for section in group.get("sections", []):
            # Skip hidden subcategories
            if section.get("published") is False:
                continue
            section_articles = [
                a for a in all_articles
                if a.get("nav_group_key") == group["key"] and a.get("section_key") == section["key"]
            ]
            pages = [{"page": a["slug"], "title": a.get("published_title") or a["title"], "icon": a.get("icon", "")} for a in section_articles]
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
            "title": a.get("published_title") or a["title"],
            "content": a.get("published_content_markdown") or a.get("content_markdown", ""),
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
        "tabs_enabled": tabs_enabled,
    }

    return {"project": project, "config": config, "documents": documents}


@router.get("/sitemap.xml")
async def sitemap_xml():
    """Dynamic sitemap of published KB articles. Public (no auth), always
    current on request — no regeneration step. Lives under /api/kb because
    that prefix is guaranteed reachable in every environment."""
    # SITE_URL is the public base URL, e.g. "https://docs.example.com".
    # Defaults to "" when unset — in that case <loc> values are emitted WITHOUT
    # a scheme+host prefix (root-relative). SET SITE_URL IN PRODUCTION so
    # crawlers receive absolute URLs.
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    articles = list(
        kb_articles.find({"published": True}, {"_id": 0, "slug": 1, "updated_at": 1}).sort("order", 1)
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        f"  <url><loc>{escape(site_url + '/')}</loc></url>",  # docs homepage, no lastmod
    ]
    for a in articles:
        loc = escape(f"{site_url}/docs/{a['slug']}")
        entry = f"  <url><loc>{loc}</loc>"
        upd = a.get("updated_at")
        lastmod = None
        if isinstance(upd, datetime):
            lastmod = upd.date().isoformat()
        elif upd:
            s = str(upd)
            lastmod = s[:10] if len(s) >= 10 else None
        if lastmod:
            entry += f"<lastmod>{lastmod}</lastmod>"
        entry += "</url>"
        lines.append(entry)
    lines.append("</urlset>")
    return Response(content="\n".join(lines), media_type="application/xml")


@router.get("/articles")
async def list_articles(nav_group: Optional[str] = None, section: Optional[str] = None):
    query = {"published": True}
    if nav_group:
        query["nav_group_key"] = nav_group
    if section:
        query["section_key"] = section
    articles = list(kb_articles.find(query, {"_id": 0, "content_markdown": 0, "published_content_markdown": 0}).sort("order", 1))
    for a in articles:
        a["title"] = a.get("published_title") or a.get("title")
    return {"articles": articles}


@router.get("/articles/{slug}")
async def get_article(slug: str):
    article = kb_articles.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    # Prefer the published snapshot; fall back to live content when absent
    # (keeps already-published articles rendering with zero backfill).
    article["content_markdown"] = article.get("published_content_markdown") or article.get("content_markdown", "")
    article["title"] = article.get("published_title") or article.get("title")
    # Get prev/next for navigation
    order = article.get("order", 0)
    prev_art = kb_articles.find_one(
        {"published": True, "order": {"$lt": order}},
        {"_id": 0, "slug": 1, "title": 1, "published_title": 1},
        sort=[("order", -1)]
    )
    next_art = kb_articles.find_one(
        {"published": True, "order": {"$gt": order}},
        {"_id": 0, "slug": 1, "title": 1, "published_title": 1},
        sort=[("order", 1)]
    )
    if prev_art:
        prev_art["title"] = prev_art.get("published_title") or prev_art.get("title")
        prev_art.pop("published_title", None)
    if next_art:
        next_art["title"] = next_art.get("published_title") or next_art.get("title")
        next_art.pop("published_title", None)
    return {
        "article": article,
        "prev": prev_art,
        "next": next_art,
    }


# ── Feedback ───────────────────────────────────────────────────

class FeedbackBody(BaseModel):
    helpful: bool
    reason: Optional[str] = None
    comment: Optional[str] = None

@router.post("/articles/{slug}/feedback")
async def submit_feedback(slug: str, body: FeedbackBody):
    article = kb_articles.find_one({"slug": slug, "published": True})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    kb_feedback.insert_one({
        "article_slug": slug,
        "helpful": body.helpful,
        "reason": body.reason,
        "comment": (body.comment or "").strip() or None,
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
        {"_id": 0, "slug": 1, "title": 1, "section_key": 1, "nav_group_key": 1,
         "nav_group_label": 1, "section_label": 1, "content_markdown": 1}
    ).sort("order", 1).limit(20))
    # Generate snippets
    import re as _re
    for r in results:
        content = r.pop("content_markdown", "") or ""
        # Find the query in content and extract a surrounding snippet
        match = _re.search(_re.escape(q), content, _re.IGNORECASE)
        if match:
            start = max(0, match.start() - 60)
            end = min(len(content), match.end() + 100)
            snippet = content[start:end].replace("\n", " ").strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."
            r["snippet"] = snippet
        else:
            r["snippet"] = content[:160].replace("\n", " ").strip() + ("..." if len(content) > 160 else "")
    return {"results": results}


# ── Admin endpoints ───────────────────────────────────────────

@router.get("/admin/articles")
async def admin_list_articles(current_user: dict = Depends(get_current_user)):
    # Exclude content_markdown from listing for performance (loaded on demand per-article)
    articles = list(kb_articles.find({}, {"_id": 0, "content_markdown": 0}).sort("order", 1))
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


@router.get("/admin/articles/{slug}")
async def admin_get_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single article with full content for editing."""
    article = kb_articles.find_one({"slug": slug}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.put("/admin/navigation")
async def update_navigation(body: dict, current_user: dict = Depends(get_current_user)):
    nav_groups = body.get("nav_groups", [])
    kb_navigation.update_one({}, {"$set": {"nav_groups": nav_groups, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
    return {"nav_groups": nav_groups}


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    section_key: Optional[str] = None
    section_label: Optional[str] = None
    nav_group_key: Optional[str] = None
    nav_group_label: Optional[str] = None
    content_markdown: Optional[str] = None
    published: Optional[bool] = None
    order: Optional[int] = None
    icon: Optional[str] = None
    sidebar_title: Optional[str] = None
    keywords: Optional[list] = None
    tags: Optional[list] = None


class ArticleCreate(BaseModel):
    title: str
    slug: str
    description: str = ""
    section_key: str = ""
    section_label: str = ""
    nav_group_key: str = ""
    nav_group_label: str = ""
    content_markdown: str = ""
    published: bool = False
    order: int = 0
    icon: str = ""
    sidebar_title: str = ""
    keywords: list = []
    tags: list = []


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
    # If created already-published, snapshot the published copy immediately.
    if doc.get("published") is True:
        doc["published_content_markdown"] = doc.get("content_markdown", "")
        doc["published_title"] = doc.get("title")
        doc["published_at"] = datetime.now(timezone.utc).isoformat()
    kb_articles.insert_one(doc)
    # Auto-sync navigation: ensure nav group and section exist (skip if empty keys)
    if doc.get("nav_group_key"):
        nav_doc = kb_navigation.find_one({})
        if nav_doc:
            nav_groups = nav_doc.get("nav_groups", [])
            group = next((g for g in nav_groups if g["key"] == doc["nav_group_key"]), None)
            if not group:
                nav_groups.append({"key": doc["nav_group_key"], "label": doc["nav_group_label"], "sections": [{"key": doc["section_key"], "label": doc["section_label"]}] if doc.get("section_key") else []})
                kb_navigation.update_one({}, {"$set": {"nav_groups": nav_groups}})
            elif doc.get("section_key"):
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
        # Only snapshot on an actual false->true transition of `published`, NOT
        # on every save of an already-published page (the editor always resends
        # the current published value). Use post-update values: if this same PUT
        # also changes content_markdown/title, snapshot the new value; otherwise
        # fall back to the existing stored value.
        was_published = article.get("published", False)
        becoming_published = updates.get("published") is True and not was_published
        if becoming_published:
            updates["published_content_markdown"] = updates.get("content_markdown", article.get("content_markdown", ""))
            updates["published_title"] = updates.get("title", article.get("title"))
            updates["published_at"] = datetime.now(timezone.utc).isoformat()
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


# ── Social Links ──────────────────────────────────────────────

SOCIAL_PLATFORMS = ["linkedin", "twitter", "discord", "youtube", "reddit"]


@router.get("/social-links")
async def get_social_links():
    """Public endpoint: return configured social links."""
    doc = kb_settings.find_one({"type": "social_links"}, {"_id": 0})
    if not doc:
        return {"links": {p: "" for p in SOCIAL_PLATFORMS}}
    return {"links": doc.get("links", {})}


class SocialLinksUpdate(BaseModel):
    links: dict


@router.put("/admin/social-links")
async def update_social_links(body: SocialLinksUpdate, current_user: dict = Depends(get_current_user)):
    """Admin endpoint: update social links."""
    # Only keep known platforms, strip empty values
    clean = {k: v.strip() for k, v in body.links.items() if k in SOCIAL_PLATFORMS}
    kb_settings.update_one(
        {"type": "social_links"},
        {"$set": {"links": clean, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"links": clean}


# ── Global Docs Settings ──────────────────────────────────────

class DocsSettingsUpdate(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    favicon_url: Optional[str] = None
    og_image_url: Optional[str] = None
    logo_url: Optional[str] = None
    footer_text: Optional[str] = None
    custom_domain: Optional[str] = None
    tabs_enabled: Optional[bool] = None


@router.get("/admin/docs-settings")
async def get_docs_settings(current_user: dict = Depends(get_current_user)):
    """Admin endpoint: get global docs site settings."""
    doc = kb_settings.find_one({"type": "docs_settings"}, {"_id": 0})
    if not doc:
        return {
            "meta_title": "Emergent Docs",
            "meta_description": "Documentation and guides for building with Emergent",
            "favicon_url": "",
            "og_image_url": "",
            "logo_url": "",
            "footer_text": "",
            "custom_domain": "",
            "tabs_enabled": False,
        }
    settings = {k: v for k, v in doc.items() if k not in ("type", "updated_at")}
    return settings


@router.put("/admin/docs-settings")
async def update_docs_settings(body: DocsSettingsUpdate, current_user: dict = Depends(get_current_user)):
    """Admin endpoint: update global docs site settings."""
    updates = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    updates["type"] = "docs_settings"
    updates["updated_at"] = datetime.now(timezone.utc)
    kb_settings.update_one(
        {"type": "docs_settings"},
        {"$set": updates},
        upsert=True,
    )
    doc = kb_settings.find_one({"type": "docs_settings"}, {"_id": 0})
    settings = {k: v for k, v in doc.items() if k not in ("type", "updated_at")}
    return settings


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


# ── Design Configuration ──────────────────────────────────────

class DesignConfigUpdate(BaseModel):
    accent_color: Optional[str] = None
    default_theme: Optional[str] = None
    code_theme: Optional[str] = None
    border_radius: Optional[str] = None
    font_family: Optional[str] = None
    custom_css: Optional[str] = None


@router.get("/admin/design-config")
async def get_design_config(current_user: dict = Depends(get_current_user)):
    """Admin endpoint: get design configuration."""
    doc = kb_settings.find_one({"type": "design_config"}, {"_id": 0})
    if not doc:
        return {
            "accent_color": "#00A1B2",
            "default_theme": "light",
            "code_theme": "github-dark",
            "border_radius": "rounded",
            "font_family": "system",
            "custom_css": "",
        }
    return {k: v for k, v in doc.items() if k not in ("type", "updated_at")}


@router.put("/admin/design-config")
async def update_design_config(body: DesignConfigUpdate, current_user: dict = Depends(get_current_user)):
    """Admin endpoint: update design configuration."""
    updates = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    updates["type"] = "design_config"
    updates["updated_at"] = datetime.now(timezone.utc)
    kb_settings.update_one(
        {"type": "design_config"},
        {"$set": updates},
        upsert=True,
    )
    doc = kb_settings.find_one({"type": "design_config"}, {"_id": 0})
    return {k: v for k, v in doc.items() if k not in ("type", "updated_at")}