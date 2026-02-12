"""
Routes for Knowledge Base snippets.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import json
import csv
import io
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from database import knowledge_snippets_collection
from pymongo import ASCENDING, DESCENDING
from dependencies import get_current_user
from utils import serialize_doc

router = APIRouter(prefix="/api", tags=["knowledge_base"])


@router.get("/knowledge-base")
async def list_snippets(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List all knowledge base snippets with filtering and search."""
    query = {}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]

    if tag:
        query["tags"] = tag

    if status:
        query["status"] = status

    sort_dir = DESCENDING if sort_order == "desc" else ASCENDING
    snippets = list(
        knowledge_snippets_collection.find(query, {"_id": 0})
        .sort(sort_by, sort_dir)
        .skip(skip)
        .limit(limit)
    )
    total = knowledge_snippets_collection.count_documents(query)

    # Get all unique tags for filtering
    all_tags = knowledge_snippets_collection.distinct("tags")

    return {"items": snippets, "total": total, "tags": all_tags}


@router.get("/knowledge-base/{snippet_id}")
async def get_snippet(
    snippet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a single knowledge base snippet."""
    snippet = knowledge_snippets_collection.find_one(
        {"snippet_id": snippet_id}, {"_id": 0}
    )
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@router.post("/knowledge-base")
async def create_snippet(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a new knowledge base snippet."""
    snippet_id = f"kb_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    snippet_doc = {
        "snippet_id": snippet_id,
        "title": (data.get("title") or "Untitled Snippet").strip()[:200],
        "content": (data.get("content") or "").strip()[:50000],
        "tags": data.get("tags", []),
        "status": data.get("status", "draft"),
        "source_ticket_id": data.get("source_ticket_id"),
        "source_message_id": data.get("source_message_id"),
        "external_url": data.get("external_url", ""),
        "snippet_type": data.get("snippet_type", "internal"),
        "created_by": current_user["user_id"],
        "created_by_name": current_user.get("name", "Unknown"),
        "created_at": now,
        "updated_at": now,
    }

    knowledge_snippets_collection.insert_one(snippet_doc)
    del snippet_doc["_id"]
    return snippet_doc


@router.put("/knowledge-base/{snippet_id}")
async def update_snippet(
    snippet_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a knowledge base snippet."""
    existing = knowledge_snippets_collection.find_one({"snippet_id": snippet_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Snippet not found")

    update_data = {"updated_at": datetime.now(timezone.utc)}
    for field in ["title", "content", "tags", "status", "external_url", "snippet_type"]:
        if field in data:
            update_data[field] = data[field]

    knowledge_snippets_collection.update_one(
        {"snippet_id": snippet_id}, {"$set": update_data}
    )
    updated = knowledge_snippets_collection.find_one(
        {"snippet_id": snippet_id}, {"_id": 0}
    )
    return updated


@router.delete("/knowledge-base/{snippet_id}")
async def delete_snippet(
    snippet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a knowledge base snippet."""
    existing = knowledge_snippets_collection.find_one({"snippet_id": snippet_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Snippet not found")

    knowledge_snippets_collection.delete_one({"snippet_id": snippet_id})
    return {"message": "Snippet deleted", "snippet_id": snippet_id}


@router.post("/knowledge-base/{snippet_id}/refine")
async def refine_snippet(
    snippet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Use AI to refine a snippet's content into a polished KB article."""
    snippet = knowledge_snippets_collection.find_one(
        {"snippet_id": snippet_id}, {"_id": 0}
    )
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    raw_content = snippet.get("content", "")
    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="Snippet has no content to refine")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=api_key,
            session_id=f"kb_refine_{snippet_id}_{uuid.uuid4().hex[:8]}",
            system_message=(
                "You are a technical writer for a customer support knowledge base. "
                "Your job is to take a raw support agent reply and transform it into a clean, "
                "concise, well-structured knowledge base article snippet. "
                "Rules: "
                "- Keep it concise and actionable. "
                "- Use clear headings if the content warrants it. "
                "- Remove any agent-specific language (e.g., 'I'll look into this', 'Hope this helps'). "
                "- Keep the tone professional and helpful. "
                "- Preserve all technical details and steps. "
                "- Output ONLY the refined article text, no preamble."
            ),
        ).with_model("gemini", "gemini-3-flash-preview")

        title = snippet.get("title", "")
        prompt = f"Title: {title}\n\nRaw agent reply:\n{raw_content}"
        user_message = UserMessage(text=prompt)
        refined = await chat.send_message(user_message)

        # Also generate a better title if the current one is generic
        if title.lower() in ["untitled snippet", ""] or len(title) < 5:
            title_chat = LlmChat(
                api_key=api_key,
                session_id=f"kb_title_{snippet_id}_{uuid.uuid4().hex[:8]}",
                system_message="Generate a short, descriptive title (max 10 words) for this knowledge base article. Output ONLY the title, nothing else.",
            ).with_model("gemini", "gemini-3-flash-preview")
            title_msg = UserMessage(text=refined)
            new_title = await title_chat.send_message(title_msg)
            new_title = new_title.strip().strip('"').strip("'")[:200]
        else:
            new_title = title

        # Update the snippet
        knowledge_snippets_collection.update_one(
            {"snippet_id": snippet_id},
            {
                "$set": {
                    "content": refined.strip(),
                    "title": new_title,
                    "status": "refined",
                    "refined_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        updated = knowledge_snippets_collection.find_one(
            {"snippet_id": snippet_id}, {"_id": 0}
        )
        return updated

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI refinement failed: {str(e)}")


@router.get("/knowledge-base-export")
async def export_snippets(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """Export all knowledge base snippets as JSON or CSV."""
    snippets = list(
        knowledge_snippets_collection.find({}, {"_id": 0}).sort("updated_at", DESCENDING)
    )

    # Convert datetime objects to ISO strings
    for s in snippets:
        for key in ["created_at", "updated_at", "refined_at"]:
            if key in s and s[key]:
                s[key] = s[key].isoformat() if hasattr(s[key], "isoformat") else str(s[key])
        if "tags" in s and isinstance(s["tags"], list):
            s["tags"] = ", ".join(s["tags"]) if format == "csv" else s["tags"]

    if format == "csv":
        output = io.StringIO()
        if snippets:
            # Collect all unique keys from all snippets for consistent CSV columns
            all_keys = set()
            for s in snippets:
                all_keys.update(s.keys())
            # Sort keys for consistent column order
            fieldnames = sorted(all_keys)
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(snippets)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=knowledge_base.csv"},
        )

    return StreamingResponse(
        iter([json.dumps(snippets, indent=2, default=str)]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=knowledge_base.json"},
    )


@router.get("/knowledge-base-search")
async def search_snippets(
    q: str = "",
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Quick search for KB snippets (used by the picker in ticket replies)."""
    if not q.strip():
        # Return recent published snippets
        snippets = list(
            knowledge_snippets_collection.find(
                {"status": {"$in": ["published", "refined"]}}, {"_id": 0}
            )
            .sort("updated_at", DESCENDING)
            .limit(limit)
        )
        return {"items": snippets}

    query = {
        "$and": [
            {"status": {"$in": ["published", "refined"]}},
            {
                "$or": [
                    {"title": {"$regex": q, "$options": "i"}},
                    {"content": {"$regex": q, "$options": "i"}},
                    {"tags": {"$regex": q, "$options": "i"}},
                ]
            },
        ]
    }
    snippets = list(
        knowledge_snippets_collection.find(query, {"_id": 0})
        .sort("updated_at", DESCENDING)
        .limit(limit)
    )
    return {"items": snippets}
