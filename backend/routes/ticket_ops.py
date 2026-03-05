"""
Ticket operations: bulk update/tag/close, merge-consecutive, merge/unmerge/link/unlink/split.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4
import uuid
import asyncio
import logging

from pymongo import ASCENDING, DESCENDING

from database import (
    db, tickets_collection, users_collection, teams_collection,
    messages_collection, ticket_changelog_collection,
)
from dependencies import get_current_user
from models.schemas import BulkUpdateRequest, BulkTagRequest
from utils import (
    serialize_doc, log_ticket_change, log_ticket_changes_batch,
    trigger_webhooks,
)
from realtime import broadcast_ticket_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ticket_ops"])

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
    
    # Batch insert changelog entries
    changelog_entries = []
    now = datetime.now(timezone.utc)
    for ticket_id in request.ticket_ids:
        for field, new_value in update_fields.items():
            if field != "updated_at":
                changelog_entries.append({
                    "changelog_id": f"cl_{uuid.uuid4().hex[:12]}",
                    "ticket_id": ticket_id,
                    "field": field,
                    "old_value": None,  # Unknown in bulk operation
                    "new_value": new_value,
                    "changed_by": current_user.get("user_id"),
                    "changed_by_name": current_user.get("name"),
                    "timestamp": now,
                    "bulk_operation": True
                })
    if changelog_entries:
        ticket_changelog_collection.insert_many(changelog_entries)
    
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
    
    query = {"ticket_id": {"$in": request.ticket_ids}}
    
    # MongoDB doesn't allow $addToSet and $pull in the same operation,
    # so we run two update_many calls instead of per-ticket loops
    if request.tags_to_add:
        tickets_collection.update_many(
            query,
            {"$addToSet": {"tags": {"$each": request.tags_to_add}}}
        )
    if request.tags_to_remove:
        tickets_collection.update_many(
            query,
            {"$pull": {"tags": {"$in": request.tags_to_remove}}}
        )
    
    return {
        "message": f"Updated tags for {len(request.ticket_ids)} tickets",
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
            "status": "closed",
            "resolved_at": now,
            "updated_at": now
        }}
    )
    
    return {
        "message": f"Closed {result.modified_count} tickets",
        "modified": result.modified_count
    }




# customers routes extracted to routes/customers.py

@router.post("/tickets/{ticket_id}/merge-consecutive")
async def merge_consecutive_tickets(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Merge consecutive tickets from the same customer into this ticket.
    Useful for when customer sends multiple emails that should be one conversation.
    """
    target_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = target_ticket.get("customer_email")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Ticket has no customer email")
    
    # Get customer to find all their emails
    customer = customers_collection.find_one({
        "$or": [
            {"primary_email": customer_email.lower()},
            {"linked_emails": customer_email.lower()}
        ]
    })
    
    customer_emails = [customer_email.lower()]
    if customer:
        customer_emails = [customer["primary_email"]] + customer.get("linked_emails", [])
    
    # Find consecutive tickets from same customer within 24 hours
    target_created = target_ticket.get("created_at")
    if isinstance(target_created, str):
        target_created = datetime.fromisoformat(target_created.replace("Z", "+00:00"))
    
    time_window_start = target_created - timedelta(hours=24)
    time_window_end = target_created + timedelta(hours=24)
    
    consecutive_tickets = list(tickets_collection.find({
        "ticket_id": {"$ne": ticket_id},
        "customer_email": {"$in": customer_emails},
        "created_at": {"$gte": time_window_start, "$lte": time_window_end},
        "status": {"$nin": ["closed"]}
    }).sort("created_at", 1))
    
    if not consecutive_tickets:
        return {"message": "No consecutive tickets found to merge", "merged_count": 0}
    
    merged_content = []
    merged_ticket_ids = []
    
    for ticket in consecutive_tickets:
        # Add ticket content to merged content
        merged_content.append({
            "from_ticket": ticket["ticket_id"],
            "title": ticket.get("title"),
            "content": ticket.get("content"),
            "created_at": ticket.get("created_at")
        })
        merged_ticket_ids.append(ticket["ticket_id"])
        
        # Mark source ticket as merged
        tickets_collection.update_one(
            {"ticket_id": ticket["ticket_id"]},
            {
                "$set": {
                    "status": "closed",
                    "merged_into": ticket_id,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
    
    # Add merged content as a note on target ticket
    if merged_content:
        note_content = "### Merged consecutive emails:\n\n"
        for item in merged_content:
            note_content += f"**From {item['from_ticket']}**: {item['title']}\n"
            note_content += f"{item['content']}\n\n---\n\n"
        
        messages_collection.insert_one({
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "ticket_id": ticket_id,
            "type": "note",
            "content": note_content,
            "author_id": "system",
            "author_name": "System",
            "is_internal": True,
            "created_at": datetime.now(timezone.utc)
        })
    
    return {
        "message": f"Merged {len(merged_ticket_ids)} consecutive tickets",
        "merged_count": len(merged_ticket_ids),
        "merged_tickets": merged_ticket_ids
    }




# csat routes extracted to routes/csat.py


# ==================== Ticket Merge/Link/Split APIs ====================

@router.post("/tickets/{ticket_id}/merge")
async def merge_tickets(
    ticket_id: str,
    merge_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Merge this ticket into another ticket with full conversation consolidation"""
    target_ticket_id = merge_data.get("target_ticket_id")
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    merge_timestamp = datetime.now(timezone.utc)
    
    # Determine the color index for this merge (cycle through 0-4)
    existing_merged = target_ticket.get("merged_tickets", [])
    color_index = len(existing_merged) % 5
    
    # Get the earliest timestamp from the source ticket for proper timeline ordering
    # The merge divider should appear BEFORE the source ticket's messages
    source_created_at = source_ticket.get("created_at", merge_timestamp)
    if isinstance(source_created_at, str):
        source_created_at = datetime.fromisoformat(source_created_at.replace("Z", "+00:00"))
    # Subtract 1 second so divider appears just before the first message
    divider_timestamp = source_created_at - timedelta(seconds=1)
    
    # Update existing messages: move to target ticket with merge metadata
    messages_collection.update_many(
        {"ticket_id": ticket_id},
        {"$set": {
            "ticket_id": target_ticket_id,
            "original_ticket_id": ticket_id,
            "merged_at": merge_timestamp,
            "merge_color_index": color_index
        }}
    )
    
    # Create a message from the source ticket's original content
    # This preserves the original ticket's description in the conversation
    if source_ticket.get("description"):
        original_content_msg = {
            "message_id": f"msg_{uuid4().hex[:12]}",
            "ticket_id": target_ticket_id,
            "type": "customer_reply",  # Treat as customer message for display
            "content": source_ticket.get("description", ""),
            "text": source_ticket.get("description", ""),
            "author_name": source_ticket.get("customer_name") or source_ticket.get("created_by_name") or "Customer",
            "author_email": source_ticket.get("customer_email"),
            "original_ticket_id": ticket_id,
            "merged_at": merge_timestamp,
            "merge_color_index": color_index,
            "merged_ticket_title": source_ticket.get("title", "Untitled"),
            "created_by": source_ticket.get("created_by", "import"),
            "created_at": source_ticket.get("created_at", merge_timestamp)
        }
        messages_collection.insert_one(original_content_msg)
    
    # Add a merge divider (visual separator showing the start of merged ticket messages)
    # Timestamp is set to just BEFORE the source ticket's creation so it appears first in timeline
    merge_note = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": target_ticket_id,
        "type": "merge_divider",
        "text": f"Merged from {ticket_id}: {source_ticket.get('title', 'Untitled')}",
        "original_ticket_id": ticket_id,
        "merged_ticket_title": source_ticket.get("title", "Untitled"),
        "merge_color_index": color_index,
        "created_by": current_user["user_id"],
        "created_at": divider_timestamp  # Use earlier timestamp so divider appears before messages
    }
    messages_collection.insert_one(merge_note)
    
    # Build merged ticket reference
    merged_ticket_ref = {
        "ticket_id": ticket_id,
        "original_title": source_ticket.get("title", "Untitled"),
        "merged_at": merge_timestamp,
        "merged_by": current_user["user_id"],
        "color_index": color_index,
        "message_count": messages_collection.count_documents({"original_ticket_id": ticket_id}),
        "original_status": source_ticket.get("status"),
        "original_priority": source_ticket.get("priority"),
        "original_customer_email": source_ticket.get("customer_email"),
    }
    
    # Collect all search identifiers from source
    source_identifiers = [ticket_id]
    if source_ticket.get("external_id"):
        source_identifiers.append(source_ticket["external_id"])
    if source_ticket.get("uuid"):
        source_identifiers.append(source_ticket["uuid"])
    # Include any identifiers source already had from previous merges
    source_identifiers.extend(source_ticket.get("search_identifiers", []))
    
    # Collect associated emails
    source_emails = []
    if source_ticket.get("customer_email"):
        source_emails.append(source_ticket["customer_email"])
    source_emails.extend(source_ticket.get("associated_emails", []))
    
    # Collect tags
    source_tags = source_ticket.get("tags", [])
    target_tags = target_ticket.get("tags", [])
    combined_tags = list(set(target_tags + source_tags))
    
    # Update target ticket with merged info
    existing_identifiers = target_ticket.get("search_identifiers", [target_ticket_id])
    existing_emails = target_ticket.get("associated_emails", [])
    if target_ticket.get("customer_email") and target_ticket["customer_email"] not in existing_emails:
        existing_emails.append(target_ticket["customer_email"])
    
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {
            "$push": {"merged_tickets": merged_ticket_ref},
            "$set": {
                "search_identifiers": list(set(existing_identifiers + source_identifiers)),
                "associated_emails": list(set(existing_emails + source_emails)),
                "tags": combined_tags,
                "updated_at": merge_timestamp
            }
        }
    )
    
    # Mark source ticket as merged (soft delete but keep for unmerge)
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "status": "merged",
            "merged_into": target_ticket_id,
            "merged_at": merge_timestamp,
            "merged_by": current_user["user_id"],
            "pre_merge_status": source_ticket.get("status", "todo")
        }}
    )
    
    # Log the change
    log_ticket_change(ticket_id, source_ticket.get("uuid", ""), "merge", None, target_ticket_id, current_user["user_id"], "merge")
    
    return {
        "message": f"Ticket {ticket_id} merged into {target_ticket_id}",
        "merged_ticket": merged_ticket_ref,
        "total_merged": len(existing_merged) + 1
    }


@router.post("/tickets/{ticket_id}/unmerge/{source_ticket_id}")
async def unmerge_ticket(
    ticket_id: str,
    source_ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unmerge a previously merged ticket, restoring it as a separate ticket"""
    # Get the parent ticket
    parent_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not parent_ticket:
        raise HTTPException(status_code=404, detail="Parent ticket not found")
    
    # Check if source_ticket_id is in merged_tickets
    merged_tickets = parent_ticket.get("merged_tickets", [])
    merged_ref = next((m for m in merged_tickets if m["ticket_id"] == source_ticket_id), None)
    
    if not merged_ref:
        raise HTTPException(status_code=400, detail=f"Ticket {source_ticket_id} was not merged into {ticket_id}")
    
    # Get the source ticket
    source_ticket = tickets_collection.find_one({"ticket_id": source_ticket_id}, {"_id": 0})
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Merged ticket record not found")
    
    unmerge_timestamp = datetime.now(timezone.utc)
    
    # Move messages back to source ticket
    messages_collection.update_many(
        {"ticket_id": ticket_id, "original_ticket_id": source_ticket_id},
        {
            "$set": {"ticket_id": source_ticket_id},
            "$unset": {"original_ticket_id": "", "merged_at": "", "merge_color_index": ""}
        }
    )
    
    # Remove merge divider message
    messages_collection.delete_many({
        "ticket_id": ticket_id,
        "type": "merge_divider",
        "original_ticket_id": source_ticket_id
    })
    
    # Remove from merged_tickets array
    updated_merged = [m for m in merged_tickets if m["ticket_id"] != source_ticket_id]
    
    # Rebuild search_identifiers (remove source's identifiers)
    source_identifiers = [source_ticket_id]
    if source_ticket.get("external_id"):
        source_identifiers.append(source_ticket["external_id"])
    if source_ticket.get("uuid"):
        source_identifiers.append(source_ticket["uuid"])
    
    current_identifiers = parent_ticket.get("search_identifiers", [])
    updated_identifiers = [i for i in current_identifiers if i not in source_identifiers]
    
    # Rebuild associated_emails
    source_email = source_ticket.get("customer_email")
    current_emails = parent_ticket.get("associated_emails", [])
    updated_emails = [e for e in current_emails if e != source_email] if source_email else current_emails
    
    # Update parent ticket
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$set": {
                "merged_tickets": updated_merged,
                "search_identifiers": updated_identifiers,
                "associated_emails": updated_emails,
                "updated_at": unmerge_timestamp
            }
        }
    )
    
    # Restore source ticket
    restore_status = source_ticket.get("pre_merge_status", "todo")
    tickets_collection.update_one(
        {"ticket_id": source_ticket_id},
        {
            "$set": {
                "status": restore_status,
                "updated_at": unmerge_timestamp
            },
            "$unset": {
                "merged_into": "",
                "merged_at": "",
                "merged_by": "",
                "pre_merge_status": ""
            }
        }
    )
    
    # Add system note to both tickets
    unmerge_note_parent = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "text": f"Unmerged ticket {source_ticket_id}: {merged_ref.get('original_title', 'Untitled')}",
        "created_by": current_user["user_id"],
        "created_at": unmerge_timestamp
    }
    messages_collection.insert_one(unmerge_note_parent)
    
    unmerge_note_source = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": source_ticket_id,
        "type": "system",
        "text": f"Unmerged from ticket {ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": unmerge_timestamp
    }
    messages_collection.insert_one(unmerge_note_source)
    
    # Log the change
    log_ticket_change(source_ticket_id, source_ticket.get("uuid", ""), "unmerge", ticket_id, None, current_user["user_id"], "unmerge")
    
    return {
        "message": f"Ticket {source_ticket_id} unmerged from {ticket_id}",
        "restored_ticket_id": source_ticket_id,
        "restored_status": restore_status,
        "remaining_merged": len(updated_merged)
    }


@router.get("/tickets/{ticket_id}/merge-suggestions")
async def get_merge_suggestions(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get auto-merge suggestions for a ticket based on same customer email within 2 hours"""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = ticket.get("customer_email")
    if not customer_email:
        return {"suggestions": []}
    
    ticket_created = ticket.get("created_at")
    if isinstance(ticket_created, str):
        ticket_created = datetime.fromisoformat(ticket_created.replace("Z", "+00:00"))
    
    # Find other open tickets from same customer within 2 hours
    two_hours_before = ticket_created - timedelta(hours=2)
    two_hours_after = ticket_created + timedelta(hours=2)
    
    suggestions = list(tickets_collection.find({
        "ticket_id": {"$ne": ticket_id},
        "customer_email": customer_email,
        "status": {"$nin": ["merged", "closed"]},
        "created_at": {
            "$gte": two_hours_before,
            "$lte": two_hours_after
        }
    }, {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "created_at": 1, "priority": 1}))
    
    return {
        "suggestions": [serialize_doc(s) for s in suggestions],
        "rule": "Same customer email within 2 hours"
    }


@router.post("/tickets/{ticket_id}/link")
async def link_tickets(
    ticket_id: str,
    link_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Link this ticket to another ticket"""
    target_ticket_id = link_data.get("target_ticket_id")
    link_type = link_data.get("link_type", "related")  # related, blocks, blocked_by, duplicates
    
    if not target_ticket_id:
        raise HTTPException(status_code=400, detail="Target ticket ID required")
    
    # Get both tickets
    source_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    target_ticket = tickets_collection.find_one({"ticket_id": target_ticket_id}, {"_id": 0})
    
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Source ticket not found")
    if not target_ticket:
        raise HTTPException(status_code=404, detail="Target ticket not found")
    
    # Add link to source ticket
    link_entry = {
        "ticket_id": target_ticket_id,
        "title": target_ticket.get("title"),
        "link_type": link_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_tickets": link_entry}}
    )
    
    # Add reverse link to target
    reverse_type = link_type
    if link_type == "blocks":
        reverse_type = "blocked_by"
    elif link_type == "blocked_by":
        reverse_type = "blocks"
    
    reverse_entry = {
        "ticket_id": ticket_id,
        "title": source_ticket.get("title"),
        "link_type": reverse_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$addToSet": {"linked_tickets": reverse_entry}}
    )
    
    # Return updated ticket
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return serialize_doc(updated_ticket)


@router.delete("/tickets/{ticket_id}/unlink/{target_ticket_id}")
async def unlink_tickets(
    ticket_id: str,
    target_ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove link between two tickets"""
    # Remove link from source
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": target_ticket_id}}}
    )
    
    # Remove link from target
    tickets_collection.update_one(
        {"ticket_id": target_ticket_id},
        {"$pull": {"linked_tickets": {"ticket_id": ticket_id}}}
    )
    
    return {"message": "Tickets unlinked"}


@router.post("/tickets/{ticket_id}/split")
async def split_ticket(
    ticket_id: str,
    split_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Split a ticket at a specific message index"""
    split_at_index = split_data.get("split_at_index")
    new_ticket_title = split_data.get("new_ticket_title")
    
    if split_at_index is None:
        raise HTTPException(status_code=400, detail="Split index required")
    
    # Get original ticket
    original_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not original_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Get all messages for this ticket
    messages = list(messages_collection.find({"ticket_id": ticket_id}, {"_id": 0}).sort("created_at", ASCENDING))
    
    if split_at_index <= 0 or split_at_index > len(messages):
        raise HTTPException(status_code=400, detail="Invalid split index")
    
    # Create new ticket - assign to the person who performed the split
    new_ticket_id = generate_ticket_id()
    new_uuid = str(uuid4())
    split_timestamp = datetime.now(timezone.utc)
    
    new_ticket = {
        "ticket_id": new_ticket_id,
        "uuid": new_uuid,
        "title": new_ticket_title or f"Split from {ticket_id}",
        "description": f"This ticket was split from {ticket_id}",
        "status": original_ticket.get("status", "todo"),
        "assignee_id": current_user["user_id"],  # Assign to who performed the split
        "priority": original_ticket.get("priority", "medium"),
        "escalation_level": original_ticket.get("escalation_level", "L1"),
        "customer_email": original_ticket.get("customer_email"),
        "customer_name": original_ticket.get("customer_name"),
        "domain": original_ticket.get("domain"),
        "tags": original_ticket.get("tags", []),
        "created_by": current_user["user_id"],
        "created_at": split_timestamp,
        "updated_at": split_timestamp,
        "split_from": ticket_id,
        "is_starred": False,
        "snoozed": False,
        # Auto-link back to original ticket
        "linked_tickets": [{
            "ticket_id": ticket_id,
            "title": original_ticket.get("title"),
            "link_type": "split_from",
            "created_at": split_timestamp.isoformat()
        }]
    }
    
    tickets_collection.insert_one(new_ticket)
    
    # Add link from original ticket to new ticket
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$addToSet": {"linked_tickets": {
            "ticket_id": new_ticket_id,
            "title": new_ticket.get("title"),
            "link_type": "split_to",
            "created_at": split_timestamp.isoformat()
        }}}
    )
    
    # Move messages after split point to new ticket
    messages_to_move = [m.get("message_id") for m in messages[split_at_index:]]
    if messages_to_move:
        messages_collection.update_many(
            {"message_id": {"$in": messages_to_move}},
            {"$set": {"ticket_id": new_ticket_id, "split_from": ticket_id}}
        )
    
    # Add system notes to both tickets
    split_note_original = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": ticket_id,
        "type": "system",
        "text": f"Ticket split. {len(messages_to_move)} message(s) moved to {new_ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": split_timestamp
    }
    messages_collection.insert_one(split_note_original)
    
    split_note_new = {
        "message_id": f"msg_{uuid4().hex[:12]}",
        "ticket_id": new_ticket_id,
        "type": "system",
        "text": f"This ticket was split from {ticket_id}",
        "created_by": current_user["user_id"],
        "created_at": split_timestamp
    }
    messages_collection.insert_one(split_note_new)
    
    # Log the change
    log_ticket_change(ticket_id, original_ticket.get("uuid", ""), "split", None, new_ticket_id, current_user["user_id"], "split")
    
    # Get updated original ticket for response
    updated_original = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    
    return {
        "message": "Ticket split successfully",
        "new_ticket_id": new_ticket_id,
        "messages_moved": len(messages_to_move),
        "updated_ticket": serialize_doc(updated_original) if updated_original else None
    }


# ==================== Feature Requests APIs ====================
