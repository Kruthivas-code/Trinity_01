"""
Review Mode: PM/reviewer workflow for the public Knowledge Base — page
assignments, threaded comments, verdicts, an activity feed, and a read-only
MIS (management) dashboard, plus a review-gated publish/unpublish action.

Ported from help-doc-v3's review_routes.py and adapted to Trinity's own
conventions:
  - Trinity uses synchronous PyMongo (no motor/await on db calls, no .to_list()).
  - Trinity's get_current_user returns a plain dict, not an object.
  - Trinity already has a real role system (agent/lead/admin) — "owner" in the
    source maps to Trinity's existing "admin" role rather than introducing a
    second, parallel privilege system.
  - Trinity's KB is single-project (no project_id) and each kb_articles doc
    already carries nav_group_key/section_key, so tab/group/page scoping reads
    straight off kb_articles instead of a separate navigation-tree lookup.
  - kb_articles has no draft/published content split — editors always edit
    content_markdown directly via the existing KB editor, unchanged. The
    publish gate here is an ADDITIONAL, optional path (POST .../publish) that
    checks for open comments / missing alt text before flipping the same
    `published` flag the existing editor already uses. The existing
    PUT /api/kb/admin/articles/{slug} endpoint is untouched and still works
    exactly as before for anyone who wants to publish without going through
    review.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from database import db, users_collection
from dependencies import get_current_user

router = APIRouter(prefix="/api/review", tags=["kb_review"])

kb_articles = db["kb_articles"]
kb_navigation = db["kb_navigation"]
review_assignments = db["kb_review_assignments"]
review_comments_col = db["kb_review_comments"]
review_verdicts_col = db["kb_review_verdicts"]
review_activity_col = db["kb_review_activity"]
review_audio_files = db["kb_review_audio_files"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _norm(email):
    return (email or "").strip().lower()


def is_owner(user: dict) -> bool:
    """Review-mode "owner" == Trinity's existing "admin" role."""
    return (user or {}).get("role") == "admin"


def _owner_only(user: dict):
    if not is_owner(user):
        raise HTTPException(status_code=403, detail="Only an admin can do this.")


def count_images_missing_alt(content: str) -> int:
    """Real content images that would ship without alt text. Ignores code (fenced blocks
    and inline `code`) so prose mentions like `<img>` don't count, and only counts
    <Figure>/<img> tags that actually have a src=. Markdown ![](url) with an empty alt is
    flagged; an explicit alt="" on a component is treated as decorative and NOT flagged."""
    content = content or ""
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'~~~.*?~~~', '', content, flags=re.DOTALL)
    content = re.sub(r'`[^`]*`', '', content)
    missing = len(re.findall(r'!\[\s*\]\([^)\s]+\)', content))
    for m in re.finditer(r'<(?:Figure|img)\b[^>]*?/?>', content, re.IGNORECASE):
        tag = m.group(0)
        if re.search(r'\bsrc\s*=', tag, re.IGNORECASE) and not re.search(r'\balt\s*=', tag, re.IGNORECASE):
            missing += 1
    return missing


def log_activity(action: str, actor_email: str, actor_name: Optional[str] = None,
                  doc_slug: Optional[str] = None, doc_title: Optional[str] = None,
                  meta: Optional[dict] = None):
    review_activity_col.insert_one({
        "id": str(uuid.uuid4()),
        "action": action,
        "actor_email": _norm(actor_email),
        "actor_name": actor_name,
        "doc_slug": doc_slug,
        "doc_title": doc_title,
        "meta": meta or {},
        "created_at": _now(),
    })


def _unassign_slugs(slugs, keep_id=None):
    """Enforce one-assignee-per-page: strip these slugs from every other assignment
    doc (deleting any that become empty) so a page is never assigned to two reviewers."""
    sset = {s for s in (slugs or []) if s}
    if not sset:
        return
    docs = list(review_assignments.find({"slugs": {"$in": list(sset)}}, {"_id": 0}))
    for a in docs:
        if keep_id and a.get("id") == keep_id:
            continue
        remaining = [s for s in (a.get("slugs") or []) if s not in sset]
        if remaining:
            review_assignments.update_one({"id": a["id"]}, {"$set": {"slugs": remaining, "updated_at": _now()}})
        else:
            review_assignments.delete_one({"id": a["id"]})


def flatten_scope_slugs(scope_type: str, scope_id: str):
    """tab -> nav_group_key, group -> "tab_key::section_key" (or bare section_key), page -> itself."""
    if scope_type == "page":
        return [scope_id]
    if scope_type == "tab":
        return [a["slug"] for a in kb_articles.find({"nav_group_key": scope_id}, {"_id": 0, "slug": 1})]
    if scope_type == "group":
        tab_key, sep, section_key = scope_id.partition("::")
        if not sep:  # unqualified — match section_key alone
            section_key = tab_key
            query = {"section_key": section_key}
        else:
            query = {"nav_group_key": tab_key, "section_key": section_key}
        return [a["slug"] for a in kb_articles.find(query, {"_id": 0, "slug": 1})]
    return []


# ---------------- Roles ----------------
@router.get("/roles/me")
async def roles_me(user: dict = Depends(get_current_user)):
    return {"email": user.get("email"), "role": user.get("role", "agent"), "is_owner": is_owner(user)}


@router.get("/known-emails")
async def known_emails(user: dict = Depends(get_current_user)):
    """Suggestion list for @mention / assign autocomplete: everyone we already know about."""
    emails = set()
    for u in users_collection.find({}, {"_id": 0, "email": 1}):
        if u.get("email"):
            emails.add(u["email"].lower())
    for a in review_assignments.find({}, {"_id": 0, "assignee_email": 1}):
        if a.get("assignee_email"):
            emails.add(a["assignee_email"].lower())
    return {"emails": sorted(emails)}


# ---------------- Publish gate ----------------
@router.post("/articles/{slug}/publish")
async def publish_article(slug: str, user: dict = Depends(get_current_user)):
    _owner_only(user)
    article = kb_articles.find_one({"slug": slug}, {"_id": 0})
    if not article:
        raise HTTPException(404, "Article not found")
    open_ct = review_comments_col.count_documents({"doc_slug": slug, "resolved": False})
    if open_ct > 0:
        raise HTTPException(400, f"Resolve all {open_ct} open comment(s) on this page before publishing")
    missing_alt = count_images_missing_alt(article.get("content_markdown", ""))
    if missing_alt > 0:
        raise HTTPException(400, f"{missing_alt} image(s) on this page are missing alt text. Add alt text (or mark them decorative) before publishing.")
    now = _now()
    kb_articles.update_one({"slug": slug}, {"$set": {"published": True, "review_status": "published", "updated_at": now}})
    log_activity("published", user.get("email"), user.get("name"), doc_slug=slug, doc_title=article.get("title"))
    return {"status": "published", "published_at": now}


@router.post("/articles/{slug}/unpublish")
async def unpublish_article(slug: str, user: dict = Depends(get_current_user)):
    _owner_only(user)
    article = kb_articles.find_one({"slug": slug}, {"_id": 0})
    if not article:
        raise HTTPException(404, "Article not found")
    kb_articles.update_one({"slug": slug}, {"$set": {"published": False, "review_status": "in_review", "updated_at": _now()}})
    log_activity("unpublished", user.get("email"), user.get("name"), doc_slug=slug, doc_title=article.get("title"))
    return {"status": "unpublished"}


# ---------------- Assignments ----------------
class AssignmentReq(BaseModel):
    scope_type: str  # tab | group | page
    scope_id: str
    scope_label: Optional[str] = ""
    assignee_email: str
    due_date: Optional[str] = None


class AssignmentStatusReq(BaseModel):
    status: str  # in_review | done


class DelegateReq(BaseModel):
    email: str


class BulkDelegateReq(BaseModel):
    from_email: str
    to_email: str


class DelegatePagesReq(BaseModel):
    from_email: str
    to_email: str
    slugs: list[str] = []


@router.post("/assignments")
async def create_assignment(req: AssignmentReq, user: dict = Depends(get_current_user)):
    _owner_only(user)
    slugs = flatten_scope_slugs(req.scope_type, req.scope_id)
    # One assignee per page: pull these pages out of any existing assignment first.
    _unassign_slugs(slugs)
    a = {"id": str(uuid.uuid4()), "scope_type": req.scope_type,
         "scope_id": req.scope_id, "scope_label": req.scope_label or req.scope_id,
         "assignee_email": _norm(req.assignee_email), "assigned_by": user.get("email"),
         "assigned_by_name": user.get("name"),
         "status": "in_review", "slugs": slugs, "delegated_from": None,
         "due_date": req.due_date,
         "created_at": _now(), "updated_at": _now()}
    review_assignments.insert_one({**a})
    if slugs:
        kb_articles.update_many(
            {"slug": {"$in": slugs}, "review_status": {"$exists": False}},
            {"$set": {"review_status": "in_review"}})
    a.pop("_id", None)
    log_activity("assigned", user.get("email"), user.get("name"),
                 doc_slug=(slugs[0] if len(slugs) == 1 else None),
                 doc_title=req.scope_label or req.scope_id,
                 meta={"assignee": _norm(req.assignee_email),
                       "scope": req.scope_label or req.scope_id, "count": len(slugs)})
    return a


@router.get("/assignments")
async def list_assignments(mine: bool = False, user: dict = Depends(get_current_user)):
    q = {}
    if mine or not is_owner(user):
        q["assignee_email"] = _norm(user.get("email"))
    items = list(review_assignments.find(q, {"_id": 0}).sort("created_at", -1).limit(500))
    return {"assignments": items}


@router.put("/assignments/{aid}")
async def update_assignment(aid: str, req: AssignmentStatusReq, user: dict = Depends(get_current_user)):
    a = review_assignments.find_one({"id": aid})
    if not a:
        raise HTTPException(404, "Assignment not found")
    if not is_owner(user) and _norm(user.get("email")) != a.get("assignee_email"):
        raise HTTPException(403, "Only an admin or the assignee can update this")
    upd = {"status": req.status, "updated_at": _now()}
    if req.status == "done":
        upd["done_at"] = a.get("done_at") or _now()
    review_assignments.update_one({"id": aid}, {"$set": upd})
    return {"status": req.status}


@router.post("/assignments/{aid}/delegate")
async def delegate_assignment(aid: str, req: DelegateReq, user: dict = Depends(get_current_user)):
    a = review_assignments.find_one({"id": aid})
    if not a:
        raise HTTPException(404, "Assignment not found")
    if not is_owner(user) and _norm(user.get("email")) != a.get("assignee_email"):
        raise HTTPException(403, "Only an admin or the current assignee can delegate")
    _unassign_slugs(a.get("slugs") or [], keep_id=aid)
    review_assignments.update_one({"id": aid}, {"$set": {
        "assignee_email": _norm(req.email), "delegated_from": a.get("assignee_email"),
        "status": "in_review", "updated_at": _now()}})
    log_activity("delegated", user.get("email"), user.get("name"),
                 meta={"from": a.get("assignee_email"), "to": _norm(req.email), "scope": a.get("scope_label")})
    return {"assignee_email": _norm(req.email), "delegated_from": a.get("assignee_email")}


@router.delete("/assignments/{aid}")
async def delete_assignment(aid: str, user: dict = Depends(get_current_user)):
    _owner_only(user)
    review_assignments.delete_one({"id": aid})
    return {"message": "deleted"}


@router.post("/assignments/delegate-bulk")
async def delegate_bulk(req: BulkDelegateReq, user: dict = Depends(get_current_user)):
    frm, to = _norm(req.from_email), _norm(req.to_email)
    if not frm or not to:
        raise HTTPException(400, "from_email and to_email are required")
    if frm == to:
        raise HTTPException(400, "Already assigned to that email")
    if not is_owner(user) and _norm(user.get("email")) != frm:
        raise HTTPException(403, "Only an admin or the current assignee can delegate these")
    frm_docs = list(review_assignments.find({"assignee_email": frm}, {"_id": 0}))
    for d in frm_docs:
        _unassign_slugs(d.get("slugs") or [], keep_id=d["id"])
    res = review_assignments.update_many(
        {"assignee_email": frm},
        {"$set": {"assignee_email": to, "delegated_from": frm, "status": "in_review", "updated_at": _now()}})
    log_activity("delegated", user.get("email"), user.get("name"),
                 meta={"from": frm, "to": to, "count": res.modified_count})
    return {"reassigned": res.modified_count, "to_email": to}


@router.post("/assignments/delegate-pages")
async def delegate_pages(req: DelegatePagesReq, user: dict = Depends(get_current_user)):
    """Delegate a chosen set of pages (all / several / one) from one reviewer to another.
    Each page becomes its OWN single-page assignment for the target."""
    frm, to = _norm(req.from_email), _norm(req.to_email)
    slugs = [s for s in (req.slugs or []) if s]
    if not frm or not to or not slugs:
        raise HTTPException(400, "from_email, to_email and at least one page are required")
    if frm == to:
        raise HTTPException(400, "Already assigned to that email")
    if not is_owner(user) and _norm(user.get("email")) != frm:
        raise HTTPException(403, "Only an admin or the current assignee can delegate these")
    now = _now()
    title_docs = list(kb_articles.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "title": 1}))
    title_by = {d["slug"]: d.get("title") for d in title_docs}
    moved = 0
    for slug in slugs:
        src = list(review_assignments.find({"assignee_email": frm, "slugs": slug}))
        if not src:
            continue
        for a in src:
            remaining = [s for s in a.get("slugs", []) if s != slug]
            if remaining:
                review_assignments.update_one({"id": a["id"]}, {"$set": {"slugs": remaining, "updated_at": now}})
            else:
                review_assignments.delete_one({"id": a["id"]})
        _unassign_slugs([slug])
        existing = review_assignments.find_one({"assignee_email": to, "slugs": slug})
        if not existing:
            review_assignments.insert_one({
                "id": str(uuid.uuid4()), "scope_type": "page", "scope_id": slug,
                "scope_label": title_by.get(slug) or slug, "assignee_email": to,
                "assigned_by": user.get("email"), "assigned_by_name": user.get("name"),
                "status": "in_review", "slugs": [slug], "due_date": None,
                "delegated_from": frm, "created_at": now, "updated_at": now})
        moved += 1
    if moved:
        log_activity("delegated", user.get("email"), user.get("name"), meta={"from": frm, "to": to, "count": moved})
    return {"moved": moved, "to_email": to}


# ---------------- Comments ----------------
class CommentReq(BaseModel):
    doc_slug: str
    body: str = ""
    anchor_text: Optional[str] = None
    audio_url: Optional[str] = None
    parent_id: Optional[str] = None
    mentions: Optional[list] = None


class VerdictReq(BaseModel):
    doc_slug: str
    verdict: str


@router.get("/comments")
async def list_comments(doc_slug: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {}
    if doc_slug:
        q["doc_slug"] = doc_slug
    items = list(review_comments_col.find(q, {"_id": 0}).sort("created_at", 1).limit(1000))
    return {"comments": items}


@router.post("/comments")
async def create_comment(req: CommentReq, user: dict = Depends(get_current_user)):
    c = {"id": str(uuid.uuid4()), "doc_slug": req.doc_slug,
         "author_email": _norm(user.get("email")), "author_name": user.get("name"), "body": req.body,
         "anchor_text": req.anchor_text, "audio_url": req.audio_url, "transcript": None,
         "parent_id": req.parent_id, "mentions": [_norm(m) for m in (req.mentions or [])],
         "resolved": False, "resolved_by": None, "read_by": [_norm(user.get("email"))], "created_at": _now()}
    review_comments_col.insert_one({**c})
    c.pop("_id", None)
    log_activity("replied" if req.parent_id else "commented", user.get("email"), user.get("name"),
                 doc_slug=req.doc_slug, meta={"mentions": c["mentions"]})
    return c


@router.post("/comments/{cid}/resolve")
async def resolve_comment(cid: str, user: dict = Depends(get_current_user)):
    c = review_comments_col.find_one({"id": cid}, {"_id": 0, "doc_slug": 1})
    review_comments_col.update_one({"id": cid}, {"$set": {"resolved": True, "resolved_by": user.get("email")}})
    log_activity("resolved", user.get("email"), user.get("name"), doc_slug=(c or {}).get("doc_slug"))
    return {"resolved": True}


@router.post("/comments/{cid}/reopen")
async def reopen_comment(cid: str, user: dict = Depends(get_current_user)):
    review_comments_col.update_one({"id": cid}, {"$set": {"resolved": False, "resolved_by": None}})
    return {"resolved": False}


@router.post("/comments/{cid}/read")
async def read_comment(cid: str, user: dict = Depends(get_current_user)):
    review_comments_col.update_one({"id": cid}, {"$addToSet": {"read_by": _norm(user.get("email"))}})
    return {"ok": True}


@router.delete("/comments/{cid}")
async def delete_comment(cid: str, user: dict = Depends(get_current_user)):
    c = review_comments_col.find_one({"id": cid})
    if not c:
        raise HTTPException(404, "not found")
    if _norm(user.get("email")) != c.get("author_email") and not is_owner(user):
        raise HTTPException(403, "Not allowed")
    review_comments_col.delete_one({"id": cid})
    return {"message": "deleted"}


@router.post("/comments/{cid}/transcribe")
async def transcribe_comment(cid: str, user: dict = Depends(get_current_user)):
    # Fast-follow: voice-to-text not yet enabled.
    return {"transcript": None, "status": "unavailable", "message": "Voice transcription is coming soon."}


# ---------------- Voice upload (stored in MongoDB, same pattern as KB images) ----------------
@router.post("/voice")
async def upload_voice(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    content = await file.read()
    name = f"{uuid.uuid4().hex}.webm"
    review_audio_files.insert_one({
        "filename": name,
        "content_type": file.content_type or "audio/webm",
        "data": content,
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc),
        "uploaded_by": user.get("email", "unknown"),
    })
    return {"url": f"/api/review/audio/{name}"}


@router.get("/audio/{filename}")
async def get_review_audio(filename: str):
    doc = review_audio_files.find_one({"filename": filename}, {"_id": 0})
    if not doc or "data" not in doc:
        raise HTTPException(404, detail="Audio not found")
    return Response(
        content=doc["data"],
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


# ---------------- Verdicts ----------------
@router.get("/verdicts")
async def list_verdicts(doc_slug: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {}
    if doc_slug:
        q["doc_slug"] = doc_slug
    items = list(review_verdicts_col.find(q, {"_id": 0}).limit(1000))
    return {"verdicts": items}


@router.post("/verdicts")
async def set_verdict(req: VerdictReq, user: dict = Depends(get_current_user)):
    if not is_owner(user):
        assigned = review_assignments.find_one({"assignee_email": _norm(user.get("email")), "slugs": req.doc_slug})
        if not assigned:
            raise HTTPException(403, "You can only add a verdict to pages assigned to you")
    key = {"doc_slug": req.doc_slug}
    review_verdicts_col.update_one(key, {"$set": {**key, "verdict": req.verdict,
        "reviewer_email": _norm(user.get("email")), "reviewer_name": user.get("name"), "updated_at": _now()}}, upsert=True)
    log_activity("verdict", user.get("email"), user.get("name"), doc_slug=req.doc_slug, meta={"verdict": req.verdict})
    return {"verdict": req.verdict}


@router.get("/verdict-history")
async def verdict_history(doc_slug: str, user: dict = Depends(get_current_user)):
    """Timeline of verdict changes for a page (who set what, when)."""
    items = list(review_activity_col.find(
        {"doc_slug": doc_slug, "action": "verdict"}, {"_id": 0}).sort("created_at", -1).limit(200))
    return {"history": items}


# ---------------- Inbox / progress ----------------
@router.get("/inbox")
async def review_inbox(user: dict = Depends(get_current_user)):
    _owner_only(user)
    comments = list(review_comments_col.find({}, {"_id": 0}).sort("created_at", -1).limit(1000))
    me = _norm(user.get("email"))
    unread = sum(1 for c in comments if me not in (c.get("read_by") or []) and c.get("author_email") != me)
    open_ct = sum(1 for c in comments if not c.get("resolved"))
    return {"comments": comments, "unread": unread, "open": open_ct, "total": len(comments)}


@router.get("/progress")
async def review_progress(user: dict = Depends(get_current_user)):
    _owner_only(user)
    assignments = list(review_assignments.find({}, {"_id": 0}).limit(500))
    by_status = {}
    for a in assignments:
        by_status[a["status"]] = by_status.get(a["status"], 0) + 1
    docs = list(kb_articles.find({}, {"_id": 0, "published": 1}).limit(2000))
    doc_status = {"published": 0, "unpublished": 0}
    for d in docs:
        doc_status["published" if d.get("published") else "unpublished"] += 1
    return {"assignments_by_status": by_status, "docs_by_status": doc_status,
            "total_assignments": len(assignments)}


# ---------------- Activity log ----------------
@router.get("/activity")
async def get_activity(person: Optional[str] = None, limit: int = 200, user: dict = Depends(get_current_user)):
    _owner_only(user)
    q = {}
    if person:
        q["actor_email"] = person.lower()
    items = list(review_activity_col.find(q, {"_id": 0}).sort("created_at", -1).limit(min(limit, 500)))
    people = review_activity_col.distinct("actor_email", {})
    slugs = list({i["doc_slug"] for i in items if i.get("doc_slug") and not i.get("doc_title")})
    if slugs:
        docs = list(kb_articles.find({"slug": {"$in": slugs}}, {"_id": 0, "slug": 1, "title": 1}))
        tmap = {d["slug"]: d.get("title") for d in docs}
        for i in items:
            if i.get("doc_slug") and not i.get("doc_title"):
                i["doc_title"] = tmap.get(i["doc_slug"])
    return {"activity": items, "people": sorted([p for p in people if p])}


@router.get("/activity/page/{slug}")
async def get_page_activity(slug: str, user: dict = Depends(get_current_user)):
    items = list(review_activity_col.find({"doc_slug": slug}, {"_id": 0}).sort("created_at", -1).limit(500))
    return {"activity": items}


# ---------------- MIS dashboard (read-only, open to any signed-in user) ----------------
@router.get("/mis")
async def mis_dashboard(user: dict = Depends(get_current_user)):
    """Read-only management snapshot: who's assigned what, verdict funnel, comment health,
    exceptions worth a human look, and a bulk alt-text audit."""
    VERDICTS = ["Looks correct", "Needs small edits", "Wrong info", "More info needed", "Outdated", "Tone / clarity", "Other"]
    docs = list(kb_articles.find({}, {"_id": 0, "slug": 1, "title": 1, "published": 1, "content_markdown": 1}))
    title_by = {d["slug"]: d.get("title") for d in docs}
    status_by = {d["slug"]: d.get("published") for d in docs}
    asg = list(review_assignments.find({}, {"_id": 0}))
    vds = list(review_verdicts_col.find({}, {"_id": 0}).sort("created_at", 1))
    cms = list(review_comments_col.find({}, {"_id": 0}))

    latest = {}
    for v in vds:
        latest[v["doc_slug"]] = v
    assignee_by = {}
    for a in asg:
        for s in a.get("slugs", []):
            assignee_by[s] = a.get("assignee_email")
    open_by, resolved_by, cmade, cresolved = {}, {}, {}, {}
    for c in cms:
        slug = c.get("doc_slug")
        am = (c.get("author_email") or "").lower()
        if c.get("resolved"):
            resolved_by[slug] = resolved_by.get(slug, 0) + 1
            if am:
                cresolved[am] = cresolved.get(am, 0) + 1
        else:
            open_by[slug] = open_by.get(slug, 0) + 1
        cmade[am] = cmade.get(am, 0) + 1

    def is_done(s):
        v = latest.get(s)
        return bool(v and v.get("verdict") == "Looks correct" and not open_by.get(s))

    reviewers = {}
    for a in asg:
        em = a.get("assignee_email") or "unassigned"
        r = reviewers.setdefault(em, {"email": em, "assigned": 0, "done": 0, "verdicts": {k: 0 for k in VERDICTS}, "done_no_verdict": 0, "comments_made": 0, "comments_resolved": 0, "overdue": 0})
        due = a.get("due_date")
        overdue_flag = bool(due) and datetime.now(timezone.utc).date() > datetime.fromisoformat(due).date()
        for s in a.get("slugs", []):
            r["assigned"] += 1
            d = is_done(s)
            if d:
                r["done"] += 1
            v = latest.get(s)
            if v and v.get("verdict") in r["verdicts"]:
                r["verdicts"][v["verdict"]] += 1
            if d and not (v and v.get("verdict")):
                r["done_no_verdict"] += 1
            if overdue_flag and a.get("status") != "done" and not d:
                r["overdue"] += 1
    for em, r in reviewers.items():
        r["comments_made"] = cmade.get(em, 0)
        r["comments_resolved"] = cresolved.get(em, 0)
        r["pct_done"] = round(100 * r["done"] / r["assigned"]) if r["assigned"] else 0
    reviewer_rows = sorted(reviewers.values(), key=lambda x: -x["assigned"])

    assigned_slugs = set(assignee_by.keys())
    all_slugs = set(title_by.keys())
    funnel = {
        "total_pages": len(all_slugs),
        "unassigned": len([s for s in all_slugs if s not in assigned_slugs]),
        "assigned": len(assigned_slugs),
        "done": len([s for s in all_slugs if is_done(s)]),
        "published": len([s for s in all_slugs if status_by.get(s)]),
        "verdicts": {k: len([s for s in all_slugs if (latest.get(s) or {}).get("verdict") == k]) for k in VERDICTS},
        "no_verdict": len([s for s in all_slugs if not (latest.get(s) or {}).get("verdict")]),
    }

    by_day = {}
    for s, v in latest.items():
        if v.get("verdict") == "Looks correct" and v.get("created_at"):
            day = str(v["created_at"])[:10]
            by_day[day] = by_day.get(day, 0) + 1
    throughput = [{"day": k, "count": by_day[k]} for k in sorted(by_day)]

    ch_pages = []
    for s in sorted(all_slugs):
        o, rv = open_by.get(s, 0), resolved_by.get(s, 0)
        if o or rv:
            ch_pages.append({"slug": s, "title": title_by.get(s), "open": o, "resolved": rv, "hot": o >= 3})
    ch_pages.sort(key=lambda x: -x["open"])

    exc = {"done_no_verdict": [], "wrong_info_unedited": [], "looks_correct_open_nr": [], "duplicate_titles": []}
    for s in all_slugs:
        v = latest.get(s)
        if is_done(s) and not (v and v.get("verdict")):
            exc["done_no_verdict"].append({"slug": s, "title": title_by.get(s)})
        if v and v.get("verdict") == "Wrong info":
            exc["wrong_info_unedited"].append({"slug": s, "title": title_by.get(s)})
        if v and v.get("verdict") == "Looks correct" and open_by.get(s):
            exc["looks_correct_open_nr"].append({"slug": s, "title": title_by.get(s), "open": open_by.get(s)})
    seen = {}
    for s, t in title_by.items():
        seen.setdefault((t or "").strip().lower(), []).append(s)
    exc["duplicate_titles"] = [{"title": t, "slugs": v} for t, v in seen.items() if len(v) > 1]

    # Bulk alt audit — every page with images missing alt text (a publish blocker).
    alt_missing = []
    for d in docs:
        n = count_images_missing_alt(d.get("content_markdown") or "")
        if n > 0:
            alt_missing.append({"slug": d["slug"], "title": d.get("title"), "count": n, "published": d.get("published")})
    alt_missing.sort(key=lambda x: -x["count"])

    return {
        "generated_at": _now(),
        "verdict_labels": VERDICTS,
        "reviewers": reviewer_rows,
        "funnel": funnel,
        "throughput": throughput,
        "comments_health": ch_pages,
        "exceptions": exc,
        "images_missing_alt": alt_missing,
    }
