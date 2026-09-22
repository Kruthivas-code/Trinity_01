"""
Public Knowledge Base API routes.
Serves articles for the help.emergent.sh-style KB frontend.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from database import db, UNSPLASH_ACCESS_KEY
from dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from pymongo import UpdateOne
import os
import re
import uuid
import logging
import requests
from xml.sax.saxutils import escape

# Owner-gating (Phase 1): reuse review.py's is_owner()/_owner_only() rather
# than a second, parallel privilege check — "owner" here means the exact
# same thing it means in review mode (Trinity's "admin" role; see review.py's
# docstring for why). _owner_only() also carries the dynamic owner-contact
# 403 message, so importing it keeps that behavior in one place.
# _unassign_slugs (Phase 2): review.py's existing one-assignee-per-page
# cascade helper, reused here so soft-deleting a page also drops it out of
# any active review assignment — same cross-module import pattern as above,
# not a new one.
from routes.review import is_owner, _owner_only, _unassign_slugs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge_base_public"])

kb_articles = db["kb_articles"]
kb_navigation = db["kb_navigation"]
kb_image_files = db["kb_image_files"]
kb_feedback = db["kb_feedback"]
kb_settings = db["kb_settings"]
# Phase 2:
kb_article_versions = db["kb_article_versions"]
# Phase 4: guarded slug changes (see "Slug change + redirects" section below).
# One document per old_slug: {old_slug, new_slug, created_at}. old_slug is
# the effective unique key (upserted on), so a slug's redirect always points
# at wherever it last moved to.
kb_redirects = db["kb_redirects"]

# Trash retention window (help-doc-v3 parity): a soft-deleted article is kept
# for 90 days, then lazily purged the next time GET /admin/trash is called.
TRASH_RETENTION_DAYS = 90

# Every kb_articles query that serves anything other than the trash/restore
# endpoints themselves must exclude soft-deleted articles. Mongo (and
# mongomock) treat {"deleted_at": None} as matching BOTH "field absent" (an
# article that has never been trashed) and "field explicitly set to None"
# (an article that was trashed and then restored) — so this one filter
# covers every live article without needing a migration for pre-Phase-2 docs.
NOT_DELETED = {"deleted_at": None}

KB_SOURCE_API = "https://help.emergent.sh/api/public/default-project"

# ── Navigation tree helpers ───────────────────────────────────
#
# kb_navigation now stores a single document shaped:
#   {"groups": [NavNode, ...], "schema_version": 2, "updated_at": <datetime>}
#
# A NavNode is either:
#   {"type": "group", "key": str, "label": str, "icon": str, "published": bool,
#    "children": [NavNode, ...]}
#   {"type": "page", "slug": str}
#
# Groups nest arbitrarily deep (group.children can hold more groups and/or
# pages, in display order). Top-level groups double as the public site's
# "tabs" (see get_public_data()) — there is no separate tabs layer.
#
# Each kb_articles document keeps denormalized nav_group_key/nav_group_label
# (top-level ancestor group) and section_key/section_label (immediate parent
# group) fields for fast lookups (admin list filters, search, and
# review.py's flatten_scope_slugs). The tree itself is the source of truth
# for structure and ordering — these fields are recomputed from the tree by
# _sync_articles_from_tree() every time the tree changes, never edited by
# hand. Intermediate ancestors (above the immediate parent) are NOT captured
# in these flat fields — recursive "everything under this middle group"
# scoping has to walk the tree itself (a job for Phase 1).


def _walk_pages(nodes, trail=None):
    """Depth-first walk of a nav subtree yielding (page_node, ancestor_group_nodes)
    for every page leaf. ancestor_group_nodes runs top-level -> immediate parent."""
    trail = trail or []
    for node in nodes or []:
        if node.get("type") == "page":
            yield node, trail
        elif node.get("type") == "group":
            yield from _walk_pages(node.get("children", []), trail + [node])


def _find_group(nodes, key):
    """Recursively find a group node by its key anywhere in the tree."""
    for node in nodes or []:
        if node.get("type") == "group":
            if node.get("key") == key:
                return node
            found = _find_group(node.get("children", []), key)
            if found is not None:
                return found
    return None


def _prune_slug(nodes, slug):
    """Return (new_nodes, changed) with any page node for this slug removed,
    anywhere in the (sub)tree. Does not mutate the input list in place."""
    changed = False
    new_nodes = []
    for node in nodes or []:
        if node.get("type") == "page" and node.get("slug") == slug:
            changed = True
            continue
        if node.get("type") == "group":
            new_children, sub_changed = _prune_slug(node.get("children", []), slug)
            node = {**node, "children": new_children}
            changed = changed or sub_changed
        new_nodes.append(node)
    return new_nodes, changed


def _find_page_location(nodes, slug, parent_key=None):
    """Locate a page node's exact spot in the nav tree: which group `key` it
    is a direct child of (None if it sits at the top level of the tree,
    outside any group), and its index within that parent's `children` list.
    Used by delete_article to record trash_nav so restore_article can put
    the page back exactly where it was."""
    for i, node in enumerate(nodes or []):
        if node.get("type") == "page" and node.get("slug") == slug:
            return {"parent_key": parent_key, "index": i}
        if node.get("type") == "group":
            found = _find_page_location(node.get("children", []), slug, node.get("key"))
            if found is not None:
                return found
    return None


def _sync_articles_from_tree(nav_groups):
    """Walk the nav tree depth-first and recompute every referenced article's
    nav_group_key/nav_group_label/section_key/section_label/order to match its
    current position in the tree. Called after every navigation write so the
    denormalized fields never drift from the structure the tree defines."""
    ops = []
    order = 0
    for page_node, ancestors in _walk_pages(nav_groups):
        slug = page_node.get("slug")
        if not slug:
            continue
        top = ancestors[0] if ancestors else None
        immediate = ancestors[-1] if ancestors else None
        update = {
            "nav_group_key": top.get("key") if top else "",
            "nav_group_label": top.get("label", "") if top else "",
            "section_key": immediate.get("key") if immediate else "",
            "section_label": immediate.get("label", "") if immediate else "",
            "order": order,
        }
        ops.append(UpdateOne({"slug": slug}, {"$set": update}))
        order += 1
    if ops:
        kb_articles.bulk_write(ops, ordered=False)


def migrate_flat_nav_to_tree():
    """One-time, idempotent upgrade: convert trinity's original flat
    {nav_groups: [{key, label, icon, sections: [{key, label, articles?}]}]}
    kb_navigation document into the new recursive {groups, schema_version: 2}
    tree. Safe to call on every startup:
      - a fresh DB has no kb_navigation doc (or seed_kb_articles() has already
        written the new shape directly) -> no-op.
      - a DB already on the new shape (schema_version == 2) -> no-op.
    Every existing nav_group_key/section_key on kb_articles is preserved at
    the same conceptual location: each old top-level group becomes a
    top-level tree group, each old section becomes a nested group under it,
    and its articles become page entries inside that group, in their
    existing `order`. Articles aren't read back from the old (and possibly
    stale) sections[].articles cache — they're pulled straight from
    kb_articles by (nav_group_key, section_key), which is always current.
    Any article whose nav_group_key/section_key doesn't match a group the
    flat doc knew about (e.g. a hand-edited or bulk-moved record) is still
    filed in — under an auto-created group of the same key — so nothing is
    ever dropped or silently left off the tree."""
    nav_doc = kb_navigation.find_one({})
    if nav_doc and nav_doc.get("schema_version") == 2:
        return  # already migrated
    if not nav_doc or "nav_groups" not in nav_doc:
        return  # fresh DB — seed_kb_articles() writes the new shape directly

    old_groups = nav_doc.get("nav_groups", [])
    new_groups = []
    group_index = {}       # key -> new top-level group node
    section_index = {}     # (group_key, section_key) -> new nested group node

    for g in old_groups:
        key = g.get("key")
        if not key or key in group_index:
            continue
        node = {"type": "group", "key": key, "label": g.get("label", key),
                "icon": g.get("icon", ""), "published": g.get("published", True), "children": []}
        for s in g.get("sections", []):
            skey = s.get("key")
            if not skey:
                continue
            sec_node = {"type": "group", "key": skey, "label": s.get("label", skey),
                        "icon": "", "published": s.get("published", True), "children": []}
            arts = list(kb_articles.find(
                {"nav_group_key": key, "section_key": skey},
                {"_id": 0, "slug": 1}
            ).sort("order", 1))
            sec_node["children"] = [{"type": "page", "slug": a["slug"]} for a in arts if a.get("slug")]
            section_index[(key, skey)] = sec_node
            node["children"].append(sec_node)
        group_index[key] = node
        new_groups.append(node)

    # Safety net: file in any article the flat doc didn't already account for.
    seen_slugs = {p["slug"] for sec in section_index.values() for p in sec["children"]}
    unmatched = 0
    for a in kb_articles.find({}, {"_id": 0, "slug": 1, "nav_group_key": 1, "nav_group_label": 1,
                                    "section_key": 1, "section_label": 1}).sort("order", 1):
        slug = a.get("slug")
        if not slug or slug in seen_slugs:
            continue
        gkey = a.get("nav_group_key") or "unassigned"
        skey = a.get("section_key") or "unassigned"
        if gkey not in group_index:
            gnode = {"type": "group", "key": gkey, "label": a.get("nav_group_label") or gkey,
                     "icon": "", "published": True, "children": []}
            group_index[gkey] = gnode
            new_groups.append(gnode)
        if (gkey, skey) not in section_index:
            snode = {"type": "group", "key": skey, "label": a.get("section_label") or skey,
                     "icon": "", "published": True, "children": []}
            section_index[(gkey, skey)] = snode
            group_index[gkey]["children"].append(snode)
        section_index[(gkey, skey)]["children"].append({"type": "page", "slug": slug})
        seen_slugs.add(slug)
        unmatched += 1

    kb_navigation.update_one({}, {
        "$set": {"groups": new_groups, "schema_version": 2, "updated_at": datetime.now(timezone.utc)},
        "$unset": {"nav_groups": ""},
    })
    _sync_articles_from_tree(new_groups)
    logger.info(
        f"[KB] Migrated flat navigation ({len(old_groups)} groups) to recursive tree "
        f"({len(new_groups)} top-level groups, {len(seen_slugs)} pages, {unmatched} auto-filed)."
    )


def seed_kb_articles():
    """Seed KB articles from help.emergent.sh if the collection is empty.
    Called on server startup — idempotent, only runs on fresh databases.
    Writes kb_navigation directly in the new recursive-tree shape (see the
    navigation tree helpers above) — a fresh DB never sees the old flat shape."""
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

    # Build the nav tree: each tab -> top-level group, each of its groups ->
    # a nested group, each page -> a page node (in original document order).
    nav_groups = []
    for tab in tabs:
        tab_children = []
        for group in tab.get("groups", []):
            section_key = group["group"].lower().replace(" ", "-").replace("'", "")
            page_children = [
                {"type": "page", "slug": (p.get("page") if isinstance(p, dict) else p)}
                for p in group.get("pages", [])
                if (p.get("page") if isinstance(p, dict) else p) in doc_map
            ]
            tab_children.append({
                "type": "group", "key": section_key, "label": group["group"],
                "icon": "", "published": True, "children": page_children,
            })
        nav_groups.append({
            "type": "group", "key": tab["id"], "label": tab.get("label", tab["id"]),
            "icon": tab.get("icon", "file-text"), "published": True, "children": tab_children,
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

    # Update navigation (new recursive-tree shape from the start)
    kb_navigation.delete_many({})
    kb_navigation.insert_one({"groups": nav_groups, "schema_version": 2, "updated_at": datetime.now(timezone.utc)})

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
        return {"groups": []}
    return {"groups": nav.get("groups", [])}


# Icon mapping for nav groups
NAV_GROUP_ICONS = {
    "beginners-guide": "book-open",
    "features": "zap",
    "building-your-app": "code",
    "deploy-and-manage": "rocket",
    "troubleshooting": "wrench",
}


def _tree_node_to_public(node, articles_by_slug):
    """Convert one nav-tree node (group or page) into the public
    {group, pages, groups} shape PublicDocs.jsx renders, recursing into
    nested groups to any depth. Returns None for an unpublished node, a page
    whose article is missing/unpublished, or a group that ends up empty —
    callers filter those out."""
    if node.get("type") == "page":
        a = articles_by_slug.get(node.get("slug"))
        if not a:
            return None
        return {"page": a["slug"], "title": a.get("published_title") or a["title"], "icon": a.get("icon", "")}
    if node.get("published") is False:
        return None
    pages, groups = [], []
    for child in node.get("children", []):
        converted = _tree_node_to_public(child, articles_by_slug)
        if converted is None:
            continue
        (pages if child.get("type") == "page" else groups).append(converted)
    if not pages and not groups:
        return None
    result = {"group": node.get("label", node.get("key"))}
    if pages:
        result["pages"] = pages
    if groups:
        result["groups"] = groups
    return result


@router.get("/public-data")
async def get_public_data():
    """Serve KB data in the format expected by the PublicDocs frontend (mirrors help.emergent.sh API)."""
    nav_doc = kb_navigation.find_one({}, {"_id": 0})
    nav_groups = (nav_doc or {}).get("groups", [])

    all_articles = list(kb_articles.find({"published": True, **NOT_DELETED}, {"_id": 0}).sort("order", 1))
    articles_by_slug = {a["slug"]: a for a in all_articles}

    # Public, unauthenticated flag for the optional horizontal tab switcher on
    # the docs nav. Defaults to False (today's stacked behavior) when unset.
    docs_settings_doc = kb_settings.find_one({"type": "docs_settings"}, {"_id": 0, "tabs_enabled": 1})
    tabs_enabled = bool((docs_settings_doc or {}).get("tabs_enabled", False))

    # Build navigation tabs from the nav tree — each top-level group is a
    # "tab"; everything beneath it (arbitrarily nested groups and pages)
    # becomes that tab's recursive `groups`/`pages` structure.
    tabs = []
    for top in nav_groups:
        if top.get("type") == "page":
            # Edge case (Phase 2 trash restore fallback): a page whose
            # original parent group no longer exists gets appended directly
            # to the root of the tree, outside any group. Wrap it as its own
            # single-page tab so it doesn't crash the top["key"]/children
            # lookups below, which assume every top-level node is a group.
            converted = _tree_node_to_public(top, articles_by_slug)
            if converted:
                tabs.append({"id": converted["page"], "label": converted["title"],
                             "icon": converted.get("icon") or "file-text",
                             "groups": [{"group": converted["title"], "pages": [converted]}]})
            continue
        if top.get("published") is False:
            continue
        tab_groups = []
        for child in top.get("children", []):
            if child.get("type") == "page":
                # A page filed directly under the tab (no intermediate
                # group) — wrap it as its own single-page group so
                # consumers only ever have to walk tabs[].groups[].
                converted = _tree_node_to_public(child, articles_by_slug)
                if converted:
                    tab_groups.append({"group": converted["title"], "pages": [converted]})
                continue
            converted = _tree_node_to_public(child, articles_by_slug)
            if converted:
                tab_groups.append(converted)
        tabs.append({
            "id": top["key"],
            "label": top.get("label", top["key"]),
            "icon": top.get("icon") or NAV_GROUP_ICONS.get(top["key"], "file-text"),
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

    # Phase 4: redirects for old slugs, resolved to wherever they currently
    # point (following any chain), included ONLY when the final target is a
    # live published article. PublicDocs.jsx maps this the same way
    # help-doc-v3's own PublicDocs.jsx maps its `redirects` field: if the
    # URL slug isn't in `documents`, look it up here and navigate to
    # `to_slug` — no new endpoint needed since this is the one call it
    # already makes on every load.
    redirects = []
    for r in kb_redirects.find({}, {"_id": 0, "old_slug": 1}):
        resolved = _resolve_redirect(r["old_slug"])
        if resolved:
            redirects.append({"from_slug": r["old_slug"], "to_slug": resolved})

    return {"project": project, "config": config, "documents": documents, "redirects": redirects}


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
        kb_articles.find({"published": True, **NOT_DELETED}, {"_id": 0, "slug": 1, "updated_at": 1}).sort("order", 1)
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
    query = {"published": True, **NOT_DELETED}
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
    article = kb_articles.find_one({"slug": slug, "published": True, **NOT_DELETED}, {"_id": 0})
    if not article:
        # Phase 4: a slug miss might be a page that got renamed out from under
        # this URL. Follow kb_redirects (written by update_article's guarded
        # slug-change) to a currently-live article and hand the caller enough
        # to redirect, instead of a bare 404. NOTE: the actual public site
        # (PublicDocs.jsx) doesn't call this per-article endpoint at all today
        # — it resolves everything from GET /public-data's `documents` list
        # client-side — so this is mainly for API consumers hitting this
        # route directly; PublicDocs.jsx's own redirect-following reads the
        # `redirects` list added to get_public_data() below instead.
        resolved = _resolve_redirect(slug)
        if resolved:
            return {"redirect_to": resolved}
        raise HTTPException(status_code=404, detail="Article not found")
    # Prefer the published snapshot; fall back to live content when absent
    # (keeps already-published articles rendering with zero backfill).
    article["content_markdown"] = article.get("published_content_markdown") or article.get("content_markdown", "")
    article["title"] = article.get("published_title") or article.get("title")
    # Get prev/next for navigation
    order = article.get("order", 0)
    prev_art = kb_articles.find_one(
        {"published": True, "order": {"$lt": order}, **NOT_DELETED},
        {"_id": 0, "slug": 1, "title": 1, "published_title": 1},
        sort=[("order", -1)]
    )
    next_art = kb_articles.find_one(
        {"published": True, "order": {"$gt": order}, **NOT_DELETED},
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
    article = kb_articles.find_one({"slug": slug, "published": True, **NOT_DELETED})
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
        {"published": True, **NOT_DELETED, "$or": [{"title": regex}, {"content_markdown": regex}]},
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
    # Exclude content_markdown from listing for performance (loaded on demand per-article).
    # Soft-deleted articles have their own dedicated GET /admin/trash listing —
    # excluded here (NOT_DELETED) so the regular editor list doesn't show them.
    articles = list(kb_articles.find(NOT_DELETED, {"_id": 0, "content_markdown": 0}).sort("order", 1))
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
    return {"articles": articles, "groups": (nav or {}).get("groups", [])}


@router.get("/admin/articles/{slug}")
async def admin_get_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single article with full content for editing. A soft-deleted
    article isn't editable through this path — it lives in Trash until
    restored (GET/POST /admin/trash...)."""
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/admin/can-edit/{slug}")
async def can_edit_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Tells the KB editor frontend which controls to show for the signed-in
    user on a given article: content edits (title/body) are open to anyone
    signed in, but structural controls — delete this page, edit the nav
    tree, edit global docs settings/design config — are owner-only (Phase 1).
    `slug` isn't actually used to vary the answer today (owner-ness isn't
    per-article), but the endpoint is shaped per-slug so a future per-page
    permission model doesn't need a new route."""
    return {
        "slug": slug,
        "is_owner": is_owner(current_user),
        "can_edit_content": True,
        "can_delete": is_owner(current_user),
        "can_edit_navigation": is_owner(current_user),
        "can_edit_site_settings": is_owner(current_user),
    }


@router.put("/admin/navigation")
async def update_navigation(body: dict, current_user: dict = Depends(get_current_user)):
    """Replace the whole nav tree in one shot (the editor always sends the
    full, edited tree back). Denormalized nav_group_key/section_key/order
    fields on every referenced article are recomputed to match afterwards.
    Owner-only (Phase 1): editing the nav tree is a structural mutation."""
    _owner_only(current_user)
    groups = body.get("groups", [])
    kb_navigation.update_one(
        {}, {"$set": {"groups": groups, "schema_version": 2, "updated_at": datetime.now(timezone.utc)}}, upsert=True
    )
    _sync_articles_from_tree(groups)
    return {"groups": groups}


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
    """Owner-only (Phase 1): creating a page is a structural mutation, not a
    content edit — it changes what exists, not what an existing page says."""
    _owner_only(current_user)
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
    # Auto-sync navigation: file the new page into the tree, creating the
    # target group (and its parent top-level group) if they don't exist yet.
    # nav_group_key = top-level group key, section_key = the immediate
    # (possibly nested) group the page actually lands in.
    if doc.get("nav_group_key"):
        nav_doc = kb_navigation.find_one({})
        if nav_doc:
            groups = nav_doc.get("groups", [])
            target_key = doc.get("section_key") or doc["nav_group_key"]
            target = _find_group(groups, target_key)
            if target is None:
                top = _find_group(groups, doc["nav_group_key"])
                if top is None:
                    top = {"type": "group", "key": doc["nav_group_key"],
                           "label": doc.get("nav_group_label") or doc["nav_group_key"],
                           "icon": "", "published": True, "children": []}
                    groups.append(top)
                if doc.get("section_key") and doc["section_key"] != doc["nav_group_key"]:
                    target = {"type": "group", "key": doc["section_key"],
                              "label": doc.get("section_label") or doc["section_key"],
                              "icon": "", "published": True, "children": []}
                    top.setdefault("children", []).append(target)
                else:
                    target = top
            target.setdefault("children", []).append({"type": "page", "slug": doc["slug"]})
            kb_navigation.update_one({}, {"$set": {"groups": groups}})
            _sync_articles_from_tree(groups)
    return kb_articles.find_one({"slug": body.slug}, {"_id": 0})


# ── Slug change + redirects (Phase 4) ───────────────────────────
#
# Trinity's internal links are root-relative `/docs/{slug}` (confirmed
# against frontend/src/components/docs/Cards.jsx's `navigate(href)` and
# App.js's `<Route path="/docs/:slug">` — NOT help-doc-v3's bare `/{slug}`,
# which has no `/docs` prefix in its own routing). The rewrite regex below
# matches that real format.
#
# help-doc-v3 parity, adapted to Trinity's schema: a redirect is a single
# `kb_redirects` doc keyed by `old_slug` (upserted, so re-renaming a page
# just repoints its existing redirect rather than growing a chain of dead
# entries), plus every *other* redirect whose target was the just-renamed
# old slug gets repointed to the new slug so existing chains keep resolving
# in one hop. Nav-tree repointing for the renamed page's OWN slug already
# happened below this block (unchanged Phase-0-era logic) — redirects only
# concern uncontrolled prose links in *other* articles' content.

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _internal_link_regex(slug: str) -> "re.Pattern":
    """Match `/docs/{slug}` with a slug boundary — i.e. NOT as a prefix of a
    longer slug (`/docs/deployment-types` must not match `/docs/deployment`).
    Boundary chars mirror what can legally follow a path segment in Markdown/
    MDX: a closing paren/quote (markdown link, href="..."), a `#` (anchor),
    a `?` (query string), whitespace, or end of string."""
    return re.compile(r"/docs/" + re.escape(slug) + r"(?=[)\"'#?\s]|$)")


def _count_internal_links(old_slug: str, exclude_slug: str) -> tuple:
    """Dry-run: how many OTHER live articles link to old_slug, and how many
    total link occurrences. Never mutates. Checks both content_markdown (the
    draft) and published_content_markdown (what the public site actually
    serves) since either can carry stale links after a rename."""
    pattern = _internal_link_regex(old_slug)
    pages = 0
    links = 0
    for a in kb_articles.find({"slug": {"$ne": exclude_slug}, **NOT_DELETED},
                               {"_id": 0, "slug": 1, "content_markdown": 1, "published_content_markdown": 1}):
        cnt = len(pattern.findall(a.get("content_markdown") or "")) + \
              len(pattern.findall(a.get("published_content_markdown") or ""))
        if cnt:
            pages += 1
            links += cnt
    return pages, links


def _rewrite_internal_links(old_slug: str, new_slug: str, exclude_slug: str) -> tuple:
    """Apply: rewrite `/docs/{old_slug}` -> `/docs/{new_slug}` across every
    OTHER live article's content_markdown and published_content_markdown,
    persisting via bulk_write. Returns (pages_touched, links_updated)."""
    pattern = _internal_link_regex(old_slug)
    replacement = f"/docs/{new_slug}"
    ops = []
    pages = 0
    links = 0
    for a in kb_articles.find({"slug": {"$ne": exclude_slug}, **NOT_DELETED},
                               {"_id": 0, "slug": 1, "content_markdown": 1, "published_content_markdown": 1}):
        update = {}
        cm = a.get("content_markdown") or ""
        new_cm, n1 = pattern.subn(replacement, cm)
        if n1:
            update["content_markdown"] = new_cm
        pcm = a.get("published_content_markdown") or ""
        new_pcm, n2 = pattern.subn(replacement, pcm)
        if n2:
            update["published_content_markdown"] = new_pcm
        if update:
            ops.append(UpdateOne({"slug": a["slug"]}, {"$set": update}))
            pages += 1
            links += n1 + n2
    if ops:
        kb_articles.bulk_write(ops, ordered=False)
    return pages, links


def _write_slug_redirect(old_slug: str, new_slug: str):
    """Record old_slug -> new_slug, and keep any existing chain resolvable in
    one hop: every other redirect whose target WAS old_slug now points at
    new_slug instead. Drops any redirect that would become a self-loop
    (a page renamed back to a slug it once redirected away from)."""
    now = datetime.now(timezone.utc)
    kb_redirects.update_many({"new_slug": old_slug}, {"$set": {"new_slug": new_slug, "updated_at": now}})
    # Drop any redirect that's now a self-loop. Plain Python comparison
    # rather than a Mongo-side {"$expr": {"$eq": [...]}} filter -- mongomock
    # evaluates $expr against a dummy {} probe doc internally and raises
    # KeyError on a missing field even with ignore_missing_keys, so $expr
    # doesn't reliably work here across both mongomock and real MongoDB.
    for doc in list(kb_redirects.find({}, {"_id": 0, "old_slug": 1, "new_slug": 1})):
        if doc.get("old_slug") == doc.get("new_slug"):
            kb_redirects.delete_one({"old_slug": doc["old_slug"]})
    kb_redirects.update_one(
        {"old_slug": old_slug},
        {"$set": {"old_slug": old_slug, "new_slug": new_slug, "created_at": now}},
        upsert=True,
    )


def _resolve_redirect(slug: str, max_hops: int = 10) -> Optional[str]:
    """Follow the kb_redirects chain starting at `slug` to wherever it
    currently resolves, but ONLY return a slug that is a live (published,
    not deleted) article today — a redirect to a slug that was itself
    deleted or never republished isn't useful to a caller. Bounded hop count
    guards against a pathological cycle slipping past _write_slug_redirect's
    self-loop cleanup (e.g. two independent renames racing each other)."""
    current = slug
    seen = {slug}
    for _ in range(max_hops):
        doc = kb_redirects.find_one({"old_slug": current}, {"_id": 0, "new_slug": 1})
        if not doc:
            return None
        nxt = doc["new_slug"]
        if nxt in seen:
            return None  # cycle
        seen.add(nxt)
        live = kb_articles.find_one({"slug": nxt, "published": True, **NOT_DELETED}, {"_id": 0, "slug": 1})
        if live:
            return nxt
        current = nxt
    return None


@router.get("/admin/articles/{slug}/slug-preview")
async def preview_slug_change(slug: str, new_slug: str, current_user: dict = Depends(get_current_user)):
    """Owner-only dry run for the guarded slug-change flow: how many other
    pages link to the CURRENT slug (what update_article would rewrite), plus
    whether new_slug is even available, without mutating anything. Powers
    the frontend confirmation copy ("this will update N internal links")
    before the user commits via PUT .../admin/articles/{slug}."""
    _owner_only(current_user)
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED}, {"_id": 0, "slug": 1})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    new_slug = (new_slug or "").strip().lower()
    slug_valid = bool(SLUG_PATTERN.match(new_slug)) if new_slug else False
    slug_available = slug_valid and (
        new_slug == slug or kb_articles.find_one({"slug": new_slug}) is None
    )
    pages_count, links_count = (0, 0) if new_slug == slug else _count_internal_links(slug, exclude_slug=slug)
    return {
        "old_slug": slug, "new_slug": new_slug,
        "slug_valid": slug_valid, "slug_available": slug_available,
        "pages_count": pages_count, "links_count": links_count,
    }


@router.put("/admin/articles/{slug}")
async def update_article(slug: str, body: ArticleUpdate, current_user: dict = Depends(get_current_user)):
    """Content edits (title/description/body of an EXISTING article) stay
    open to any signed-in user (Phase 1) — this endpoint does not create,
    delete or move a page, so it isn't owner-gated. Every edit stamps
    reviewer_edited_by/reviewer_edited_at so there's an audit trail of who
    touched content that isn't the owner (kept regardless of role, so an
    owner's own edits are tracked the same way). A trashed article can't be
    edited through this path — restore it first.

    Phase 4 extension: a slug change is a STRUCTURAL mutation (it changes
    the page's public address and every other page's links to it), not a
    content edit — so unlike every other field this endpoint accepts, a
    request that changes `slug` is owner-gated (_owner_only), matching how
    create/delete/navigation edits are already gated (Phase 1's own
    philosophy: content vs. structure). When it IS a slug change, this also
    performs the full safe-change: create/repoint a kb_redirects entry from
    the old slug, and rewrite every other live article's internal
    `/docs/{old_slug}` links to `/docs/{new_slug}` (content_markdown AND the
    published snapshot) in the same request — one canonical implementation,
    reused by both this endpoint and the dedicated
    GET .../slug-preview dry-run above."""
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    updates = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    slug_changing = "slug" in updates and updates["slug"] != slug
    if slug_changing:
        _owner_only(current_user)
        new_slug = updates["slug"].strip().lower()
        if not SLUG_PATTERN.match(new_slug):
            raise HTTPException(status_code=400, detail="Slug must be lowercase letters, numbers and hyphens only (e.g. my-page).")
        updates["slug"] = new_slug
        conflict = kb_articles.find_one({"slug": new_slug})
        if conflict:
            raise HTTPException(status_code=409, detail="Slug already in use")
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        updates["reviewer_edited_by"] = current_user.get("email")
        updates["reviewer_edited_at"] = updates["updated_at"].isoformat()
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
    slug_change_result = None
    # A slug change needs the matching page node in the nav tree repointed too
    # (page nodes reference articles by slug), otherwise the page becomes
    # unreachable from the sidebar even though the article itself still exists.
    if slug_changing:
        nav_doc = kb_navigation.find_one({})
        if nav_doc:
            groups = nav_doc.get("groups", [])
            for page_node, _ in _walk_pages(groups):
                if page_node.get("slug") == slug:
                    page_node["slug"] = final_slug
            kb_navigation.update_one({}, {"$set": {"groups": groups}})
        pages_touched, links_updated = _rewrite_internal_links(slug, final_slug, exclude_slug=final_slug)
        _write_slug_redirect(slug, final_slug)
        slug_change_result = {"old_slug": slug, "new_slug": final_slug,
                               "pages_touched": pages_touched, "links_updated": links_updated}
    result = kb_articles.find_one({"slug": final_slug}, {"_id": 0})
    if slug_change_result:
        result["slug_change"] = slug_change_result
    return result


@router.delete("/admin/articles/{slug}")
async def delete_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Owner-only (Phase 1): deleting a page is a structural mutation.
    Phase 2: this is now a SOFT delete (help-doc-v3 parity) — the page moves
    to Trash for 90 days rather than being destroyed outright. The
    kb_articles document is kept (just flagged), only its nav-tree entry is
    removed so it disappears from the live sidebar/public site immediately.
    See GET/POST/DELETE /admin/trash... for list/restore/permanent-delete."""
    _owner_only(current_user)
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED}, {"_id": 0, "slug": 1})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Remember exactly where this page lived in the nav tree (which group
    # `key` it was a direct child of, and its index in that group's
    # children) before pruning it out, so restore can put it back exactly
    # where it was.
    trash_nav = None
    nav_doc = kb_navigation.find_one({})
    if nav_doc:
        groups = nav_doc.get("groups", [])
        trash_nav = _find_page_location(groups, slug)
        new_groups, changed = _prune_slug(groups, slug)
        if changed:
            kb_navigation.update_one({}, {"$set": {"groups": new_groups}})
            _sync_articles_from_tree(new_groups)

    now = datetime.now(timezone.utc)
    kb_articles.update_one({"slug": slug}, {"$set": {
        "deleted_at": now,
        "deleted_by": current_user.get("email"),
        "deleted_by_name": current_user.get("name"),
        "trash_nav": trash_nav,
        "updated_at": now,
    }})
    # Cascade: this page is no longer live, so pull it out of any active
    # review assignment too (review.py's existing one-assignee-per-page
    # cascade helper — deletes the assignment doc if it becomes empty).
    _unassign_slugs([slug])
    return {"message": "Article moved to Trash"}


# ── Trash (soft-delete) ────────────────────────────────────────

@router.get("/admin/trash")
async def list_trash(current_user: dict = Depends(get_current_user)):
    """Owner-only: list soft-deleted articles, newest-deleted-first. Anything
    past the 90-day retention window is lazily hard-deleted right here on
    read (help-doc-v3 parity) — no further cascade is needed for a purge
    that happens this way, since review assignments were already cleared at
    soft-delete time."""
    _owner_only(current_user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=TRASH_RETENTION_DAYS)
    kb_articles.delete_many({"deleted_at": {"$ne": None, "$lt": cutoff}})
    items = list(kb_articles.find(
        {"deleted_at": {"$ne": None}},
        {"_id": 0, "slug": 1, "title": 1, "published": 1,
         "deleted_at": 1, "deleted_by": 1, "deleted_by_name": 1},
    ).sort("deleted_at", -1).limit(500))
    now = datetime.now(timezone.utc)
    for it in items:
        deleted_at = it.get("deleted_at")
        try:
            # PyMongo/mongomock hand back naive datetimes on read even though
            # we always write timezone-aware UTC ones on insert (the BSON
            # wire encoding is UTC-epoch based regardless of the python
            # tzinfo on the way in) — normalize before subtracting so this
            # doesn't raise on a real MongoDB instance either.
            da = deleted_at if deleted_at.tzinfo else deleted_at.replace(tzinfo=timezone.utc)
            elapsed_days = (now - da).days if isinstance(deleted_at, datetime) else 0
            it["days_left"] = max(0, TRASH_RETENTION_DAYS - elapsed_days)
        except Exception:
            it["days_left"] = TRASH_RETENTION_DAYS
    return {"trash": items}


@router.post("/admin/trash/{slug}/restore")
async def restore_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: restore a trashed article and re-insert its page node back
    into kb_navigation at the exact (parent group key, index) recorded at
    delete time. If that parent group no longer exists (e.g. it was itself
    deleted/renamed while this page sat in Trash), fall back to appending
    the page at the top level of the tree, and say so in the response."""
    _owner_only(current_user)
    article = kb_articles.find_one({"slug": slug, "deleted_at": {"$ne": None}}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Trashed article not found")

    now = datetime.now(timezone.utc)
    kb_articles.update_one({"slug": slug}, {"$set": {
        "deleted_at": None, "deleted_by": None, "deleted_by_name": None,
        "trash_nav": None, "updated_at": now,
    }})

    trash_nav = article.get("trash_nav") or {}
    parent_key = trash_nav.get("parent_key")
    index = trash_nav.get("index", 0)
    fell_back = False

    nav_doc = kb_navigation.find_one({})
    groups = (nav_doc or {}).get("groups", [])
    page_node = {"type": "page", "slug": slug}
    target = _find_group(groups, parent_key) if parent_key else None
    if target is not None:
        children = target.setdefault("children", [])
        idx = min(max(index, 0), len(children))
        children.insert(idx, page_node)
    else:
        groups.append(page_node)
        fell_back = True

    if nav_doc:
        kb_navigation.update_one({}, {"$set": {"groups": groups}})
    else:
        kb_navigation.insert_one({"groups": groups, "schema_version": 2, "updated_at": now})
    _sync_articles_from_tree(groups)

    result = {"message": "Article restored", "fell_back_to_top_level": fell_back}
    if fell_back:
        result["note"] = ("Original group no longer exists — the page was appended at the "
                           "top level of the navigation tree. Move it into place from Settings > Navigation.")
    return result


@router.delete("/admin/trash/{slug}")
async def purge_article(slug: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: permanently delete a trashed article. Irreversible. No
    further cascade needed — review assignments were already cleared when
    the article was soft-deleted."""
    _owner_only(current_user)
    article = kb_articles.find_one({"slug": slug, "deleted_at": {"$ne": None}}, {"_id": 0, "slug": 1})
    if not article:
        raise HTTPException(status_code=404, detail="Trashed article not found")
    kb_articles.delete_one({"slug": slug})
    return {"message": "Permanently deleted"}


# ── Version history ─────────────────────────────────────────────
#
# Ported from help-doc-v3's version-control endpoints. Confirmed against
# help-doc-v3/backend/server.py (DocumentVersion model + the
# /versions.../restore routes, ~lines 224-1520): a version snapshot there is
# NOT taken automatically on every save of the document-update endpoint —
# it's an explicit, user-named action ("Create Version Snapshot" in
# VersionHistoryPanel.jsx, POST .../versions with a version_name). Restore
# auto-creates one backup snapshot labeled "Auto-backup before restore to
# '<name>'" immediately before overwriting, then copies only content+title
# from the old version onto the live document — it does not touch the
# document's id/slug or its position anywhere.
#
# Trinity mirrors that exactly here: kb_article_versions holds explicit,
# unlimited-count snapshots (no auto-snapshot hook inside update_article —
# that would just be noise on every keystroke-triggered save and doesn't
# match what help-doc-v3 actually does). A snapshot captures every field
# ArticleUpdate accepts (not just content_markdown/title) since that's a
# strictly more useful historical record, but restore only ever writes back
# the CONTENT fields (title/description/content_markdown/icon/sidebar_title/
# keywords/tags) — never slug/nav_group_key/section_key/order/published —
# matching help-doc-v3's restore, which never touches structure either.

VERSION_SNAPSHOT_FIELDS = [
    "title", "slug", "description", "section_key", "section_label",
    "nav_group_key", "nav_group_label", "content_markdown", "published",
    "order", "icon", "sidebar_title", "keywords", "tags",
]
RESTORE_CONTENT_FIELDS = [
    "title", "description", "content_markdown", "icon", "sidebar_title", "keywords", "tags",
]


class CreateVersionRequest(BaseModel):
    label: Optional[str] = None


def _snapshot_article_fields(article: dict) -> dict:
    return {k: article.get(k) for k in VERSION_SNAPSHOT_FIELDS}


def _save_article_version(slug: str, article: dict, label: str, current_user: dict) -> dict:
    doc = {
        "id": str(uuid.uuid4()),
        "article_slug": slug,
        "label": label,
        "snapshot": _snapshot_article_fields(article),
        "created_by": current_user.get("email"),
        "created_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
    }
    kb_article_versions.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@router.get("/admin/articles/{slug}/versions")
async def list_article_versions(slug: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: list an article's saved versions, newest first. Snapshot
    content is omitted from the list (fetch a single version for that)."""
    _owner_only(current_user)
    versions = list(kb_article_versions.find(
        {"article_slug": slug}, {"_id": 0, "snapshot": 0}
    ).sort("created_at", -1).limit(200))
    return {"versions": versions}


@router.post("/admin/articles/{slug}/versions")
async def create_article_version(slug: str, body: CreateVersionRequest, current_user: dict = Depends(get_current_user)):
    """Owner-only: explicitly save a named snapshot of the article's current
    state (help-doc-v3 parity — versions are user-triggered, not automatic
    on every save)."""
    _owner_only(current_user)
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    label = body.label.strip() if body.label and body.label.strip() else \
        f"Saved on {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}"
    version = _save_article_version(slug, article, label, current_user)
    return {"message": "Version created", "version": version}


@router.get("/admin/articles/{slug}/versions/{version_id}")
async def get_article_version(slug: str, version_id: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: fetch one version's full snapshot."""
    _owner_only(current_user)
    version = kb_article_versions.find_one({"id": version_id, "article_slug": slug}, {"_id": 0})
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.delete("/admin/articles/{slug}/versions/{version_id}")
async def delete_article_version(slug: str, version_id: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: delete a single saved version."""
    _owner_only(current_user)
    result = kb_article_versions.delete_one({"id": version_id, "article_slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"message": "Deleted"}


@router.post("/admin/articles/{slug}/versions/{version_id}/restore")
async def restore_article_version(slug: str, version_id: str, current_user: dict = Depends(get_current_user)):
    """Owner-only: restore the article's content to a previous version.
    Auto-snapshots the CURRENT state first (labeled "Auto-backup before
    restore to '<version label>'"), then overwrites only content fields —
    slug/nav position/order/published are left untouched, matching
    help-doc-v3's restore_document_version exactly."""
    _owner_only(current_user)
    version = kb_article_versions.find_one({"id": version_id, "article_slug": slug}, {"_id": 0})
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    article = kb_articles.find_one({"slug": slug, **NOT_DELETED}, {"_id": 0})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    backup_label = f"Auto-backup before restore to '{version.get('label', 'unknown')}'"
    _save_article_version(slug, article, backup_label, current_user)

    now = datetime.now(timezone.utc)
    snap = version.get("snapshot") or {}
    restore_updates = {k: snap.get(k) for k in RESTORE_CONTENT_FIELDS if snap.get(k) is not None}
    restore_updates["updated_at"] = now
    restore_updates["reviewer_edited_by"] = current_user.get("email")
    restore_updates["reviewer_edited_at"] = now.isoformat()
    kb_articles.update_one({"slug": slug}, {"$set": restore_updates})

    return {
        "message": f"Article restored to version '{version.get('label')}'",
        "article": kb_articles.find_one({"slug": slug}, {"_id": 0}),
    }


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


@router.get("/admin/images/search-stock")
async def search_stock_images(query: str = "", page: int = 1, per_page: int = 12,
                                current_user: dict = Depends(get_current_user)):
    """Image Picker (Phase 4) — Stock tab: proxy a search to Unsplash. Same
    auth tier as POST /admin/images above (any signed-in user, not
    owner-gated — this is a content-authoring tool, not a structural one).
    Unsplash's key is server-side only (routes/kb.py never exposes it to the
    client) via UNSPLASH_ACCESS_KEY (database.py), defaulting to the public
    'demo' Client-ID exactly like help-doc-v3's server.py. On any failure
    (rate-limited demo key, network error, bad key) this returns an empty
    result with an `error` message rather than 500ing — a slow/unavailable
    third party shouldn't break the editor."""
    query = (query or "").strip()
    if not query:
        return {"images": [], "total": 0, "total_pages": 0, "page": page}
    per_page = max(1, min(per_page, 30))
    page = max(1, page)
    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "page": page, "per_page": per_page, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        logger.warning(f"[KB] Unsplash stock image search failed: {e}")
        return {"images": [], "total": 0, "total_pages": 0, "page": page,
                "error": "Stock image search is unavailable right now."}
    images = []
    for photo in result.get("results", []):
        user = photo.get("user") or {}
        images.append({
            "id": photo.get("id"),
            "url": (photo.get("urls") or {}).get("regular"),
            "thumb": (photo.get("urls") or {}).get("thumb"),
            "small": (photo.get("urls") or {}).get("small"),
            "alt": photo.get("alt_description") or photo.get("description") or query,
            "author": user.get("name", ""),
            "author_url": (user.get("links") or {}).get("html", ""),
            "source": "unsplash",
        })
    return {"images": images, "total": result.get("total", 0),
            "total_pages": result.get("total_pages", 0), "page": page}


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
    """Admin endpoint: update global docs site settings.
    Owner-only (Phase 1): global site settings are structural, not per-page
    content."""
    _owner_only(current_user)
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


# ── Bulk move articles between nav groups ──────────────────────

class BulkMoveRequest(BaseModel):
    source_key: str
    target_key: str


@router.post("/admin/articles/bulk-move")
async def bulk_move_articles(body: BulkMoveRequest, current_user: dict = Depends(get_current_user)):
    """Move every page filed directly under one nav-tree group over to another
    group, wherever either lives in the tree. Nested subgroups of the source
    are left in place — only its own direct pages move (matches the editor's
    "move all articles in this group" action). Keys, not labels: the tree
    already carries labels, so callers only need to say which groups.
    Owner-only (Phase 1): this mutates the nav tree, same as
    PUT /admin/navigation."""
    _owner_only(current_user)
    nav_doc = kb_navigation.find_one({})
    if not nav_doc:
        raise HTTPException(status_code=404, detail="Navigation not found")
    groups = nav_doc.get("groups", [])
    source = _find_group(groups, body.source_key)
    target = _find_group(groups, body.target_key)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Source or target group not found")
    moving = [c for c in source.get("children", []) if c.get("type") == "page"]
    source["children"] = [c for c in source.get("children", []) if c.get("type") != "page"]
    target.setdefault("children", []).extend(moving)
    kb_navigation.update_one({}, {"$set": {"groups": groups, "updated_at": datetime.now(timezone.utc)}})
    _sync_articles_from_tree(groups)
    return {"moved": len(moving)}


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
    """Admin endpoint: update design configuration.
    Owner-only (Phase 1): site-wide design config is structural, not
    per-page content."""
    _owner_only(current_user)
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