"""
Routes for canned responses.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from database import canned_responses_collection
from dependencies import get_current_user
from models.schemas import CannedResponseCreate, CannedResponseUpdate
from utils import serialize_doc

router = APIRouter(prefix="/api", tags=["canned_responses"])

# ==================== Canned Responses ====================

@router.get("/canned-responses")
async def get_canned_responses(
    scope: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all canned responses available to the user.
    Returns global responses + user's personal responses.
    Personal responses take priority over global when shortcodes conflict.
    """
    user_id = current_user.get("user_id")
    
    # Build query for global + user's personal responses
    query = {
        "$or": [
            {"scope": "global"},
            {"scope": "personal", "created_by": user_id}
        ]
    }
    
    # Filter by scope if specified
    if scope == "global":
        query = {"scope": "global"}
    elif scope == "personal":
        query = {"scope": "personal", "created_by": user_id}
    
    responses = list(canned_responses_collection.find(query, {"_id": 0}).sort("title", ASCENDING))
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        responses = [r for r in responses if 
                    search_lower in r.get("title", "").lower() or 
                    search_lower in r.get("shortcode", "").lower() or
                    search_lower in r.get("content", "").lower()]
    
    # Group by scope for easier frontend handling
    global_responses = [r for r in responses if r.get("scope") == "global"]
    personal_responses = [r for r in responses if r.get("scope") == "personal"]
    
    return {
        "global": global_responses,
        "personal": personal_responses,
        "all": responses
    }

@router.get("/canned-responses/{response_id}")
async def get_canned_response(
    response_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a single canned response by ID"""
    user_id = current_user.get("user_id")
    
    response = canned_responses_collection.find_one(
        {"response_id": response_id},
        {"_id": 0}
    )
    
    if not response:
        raise HTTPException(status_code=404, detail="Canned response not found")
    
    # Check access - global is accessible to all, personal only to owner
    if response.get("scope") == "personal" and response.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return response

@router.post("/canned-responses")
async def create_canned_response(
    data: CannedResponseCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new canned response"""
    user_id = current_user.get("user_id")
    shortcode = data.shortcode.lower().strip()
    
    # Check for duplicate shortcode in same scope
    existing_query = {"shortcode": shortcode}
    if data.scope == "global":
        existing_query["scope"] = "global"
    else:
        existing_query["scope"] = "personal"
        existing_query["created_by"] = user_id
    
    existing = canned_responses_collection.find_one(existing_query)
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Shortcode '/{shortcode}' already exists in {data.scope} scope"
        )
    
    response_id = f"cr_{uuid.uuid4().hex[:12]}"
    response_doc = {
        "response_id": response_id,
        "title": data.title.strip(),
        "shortcode": shortcode,
        "content": data.content,
        "scope": data.scope,
        "created_by": user_id,
        "created_by_name": current_user.get("name", "Unknown"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    canned_responses_collection.insert_one(response_doc)
    del response_doc["_id"]
    
    return response_doc

@router.put("/canned-responses/{response_id}")
async def update_canned_response(
    response_id: str,
    data: CannedResponseUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a canned response"""
    user_id = current_user.get("user_id")
    
    # Find existing response
    existing = canned_responses_collection.find_one({"response_id": response_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Canned response not found")
    
    # Check permission - personal responses can only be edited by owner
    if existing.get("scope") == "personal" and existing.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own personal responses")
    
    # Build update dict
    update_data = {"updated_at": datetime.now(timezone.utc)}
    
    if data.title is not None:
        update_data["title"] = data.title.strip()
    
    if data.shortcode is not None:
        new_shortcode = data.shortcode.lower().strip()
        # Check for duplicate shortcode
        scope = data.scope if data.scope else existing.get("scope")
        dup_query = {"shortcode": new_shortcode, "response_id": {"$ne": response_id}}
        if scope == "global":
            dup_query["scope"] = "global"
        else:
            dup_query["scope"] = "personal"
            dup_query["created_by"] = user_id
        
        if canned_responses_collection.find_one(dup_query):
            raise HTTPException(status_code=400, detail=f"Shortcode '/{new_shortcode}' already exists")
        update_data["shortcode"] = new_shortcode
    
    if data.content is not None:
        update_data["content"] = data.content
    
    if data.scope is not None:
        update_data["scope"] = data.scope
    
    canned_responses_collection.update_one(
        {"response_id": response_id},
        {"$set": update_data}
    )
    
    updated = canned_responses_collection.find_one({"response_id": response_id}, {"_id": 0})
    return updated

@router.delete("/canned-responses/{response_id}")
async def delete_canned_response(
    response_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a canned response"""
    user_id = current_user.get("user_id")
    
    # Find existing response
    existing = canned_responses_collection.find_one({"response_id": response_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Canned response not found")
    
    # Check permission - personal responses can only be deleted by owner
    if existing.get("scope") == "personal" and existing.get("created_by") != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own personal responses")
    
    canned_responses_collection.delete_one({"response_id": response_id})
    
    return {"message": "Canned response deleted", "response_id": response_id}


# ==================== Bulk Operations ====================

@router.post("/tickets/bulk-update")
async def bulk_update_tickets(
    request: BulkUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk update multiple tickets at once"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    # Validate updates
    allowed_fields = {"status", "priority", "assignee_id", "team_id", "escalation_level"}
    update_fields = {k: v for k, v in request.updates.items() if k in allowed_fields}
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid update fields provided")
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    # Perform bulk update
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": request.ticket_ids}},
        {"$set": update_fields}
    )
    
    # Log to changelog for each ticket
    for ticket_id in request.ticket_ids:
        for field, new_value in update_fields.items():
            if field != "updated_at":
                ticket_changelog_collection.insert_one({
                    "changelog_id": f"cl_{uuid.uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "field": field,
                    "old_value": None,  # Unknown in bulk operation
                    "new_value": new_value,
                    "changed_by": current_user.get("user_id"),
                    "changed_by_name": current_user.get("name"),
                    "timestamp": datetime.now(timezone.utc),
                    "bulk_operation": True
                })
    
    return {
        "message": f"Updated {result.modified_count} tickets",
        "matched": result.matched_count,
        "modified": result.modified_count
    }

@router.post("/tickets/bulk-tag")
async def bulk_tag_tickets(
    request: BulkTagRequest,
    current_user: dict = Depends(get_current_user)
):
    """Bulk add or remove tags from multiple tickets"""
    if not request.ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(request.ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    modified_count = 0
    
    for ticket_id in request.ticket_ids:
        update_ops = {}
        
        if request.tags_to_add:
            update_ops["$addToSet"] = {"tags": {"$each": request.tags_to_add}}
        
        if request.tags_to_remove:
            update_ops["$pull"] = {"tags": {"$in": request.tags_to_remove}}
        
        if update_ops:
            # MongoDB doesn't allow $addToSet and $pull in same operation
            if request.tags_to_add:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$addToSet": {"tags": {"$each": request.tags_to_add}}}
                )
            if request.tags_to_remove:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$pull": {"tags": {"$in": request.tags_to_remove}}}
                )
            modified_count += 1
    
    return {
        "message": f"Updated tags for {modified_count} tickets",
        "tags_added": request.tags_to_add,
        "tags_removed": request.tags_to_remove
    }

@router.post("/tickets/bulk-close")
async def bulk_close_tickets(
    ticket_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Bulk close multiple tickets"""
    if not ticket_ids:
        raise HTTPException(status_code=400, detail="No ticket IDs provided")
    
    if len(ticket_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tickets per bulk operation")
    
    now = datetime.now(timezone.utc)
    result = tickets_collection.update_many(
        {"ticket_id": {"$in": ticket_ids}},
        {"$set": {
            "status": "resolved",
            "resolved_at": now,
            "updated_at": now
        }}
    )
    
    return {
        "message": f"Closed {result.modified_count} tickets",
        "modified": result.modified_count
    }


