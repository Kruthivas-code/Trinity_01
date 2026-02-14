"""
Routes for AI-powered ticket summarization.
"""
from datetime import datetime, timezone
import os
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends
from database import tickets_collection, messages_collection
from dependencies import get_current_user
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["summaries"])

MIN_CUSTOMER_MESSAGES = 5


def _count_customer_messages(ticket_id: str) -> int:
    """Count customer messages (original + customer_reply) for a ticket."""
    return messages_collection.count_documents({
        "ticket_id": ticket_id,
        "type": {"$in": ["original", "customer_reply"]}
    })


def _get_conversation_text(ticket_id: str, limit: int = 50) -> str:
    """Get conversation messages as text for summarization."""
    msgs = list(messages_collection.find(
        {"ticket_id": ticket_id},
        {"_id": 0, "type": 1, "content": 1, "author_name": 1, "created_at": 1}
    ).sort("created_at", 1).limit(limit))

    lines = []
    for m in msgs:
        role = "Customer" if m.get("type") in ("original", "customer_reply") else "Agent"
        name = m.get("author_name") or role
        content = (m.get("content") or "")[:2000]
        if content.strip():
            lines.append(f"[{role} - {name}]: {content}")
    return "\n".join(lines)


def _get_past_tickets_text(customer_email: str, current_ticket_id: str, limit: int = 10) -> list:
    """Get past tickets from the same customer."""
    if not customer_email:
        return []
    past = list(tickets_collection.find(
        {"customer_email": customer_email, "ticket_id": {"$ne": current_ticket_id}},
        {"_id": 0, "ticket_id": 1, "title": 1, "status": 1, "description": 1, "created_at": 1}
    ).sort("created_at", -1).limit(limit))
    return past


async def _generate_summary(api_key: str, ticket_id: str, conversation_text: str, past_tickets: list) -> dict:
    """Generate summary using Gemini."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    result = {"conversation_summary": None, "past_issues_summary": None}

    # Conversation summary
    chat = LlmChat(
        api_key=api_key,
        session_id=f"ticket_summary_{ticket_id}_{uuid.uuid4().hex[:6]}",
        system_message=(
            "You summarize support ticket conversations in 3-5 concise lines. "
            "Focus on: what the customer's issue is, what has been tried, and current status. "
            "Be direct and factual. No preamble, no bullet points, just a short paragraph."
        ),
    ).with_model("gemini", "gemini-3-flash-preview")

    conv_response = await chat.send_message(UserMessage(text=f"Summarize this conversation:\n\n{conversation_text}"))
    result["conversation_summary"] = conv_response.strip()

    # Past issues summary
    if len(past_tickets) > 0:
        past_text = "\n".join([
            f"- Ticket {t['ticket_id']}: \"{t.get('title', 'Untitled')}\" (Status: {t.get('status', 'unknown')}) - {(t.get('description') or '')[:300]}"
            for t in past_tickets
        ])

        past_chat = LlmChat(
            api_key=api_key,
            session_id=f"past_summary_{ticket_id}_{uuid.uuid4().hex[:6]}",
            system_message=(
                "You summarize a customer's past support tickets in 3-5 concise lines. "
                "Mention the key issues and their outcomes. "
                "Be direct and factual. No preamble, no bullet points, just a short paragraph."
            ),
        ).with_model("gemini", "gemini-3-flash-preview")

        past_response = await past_chat.send_message(UserMessage(text=f"Summarize these past tickets from the same customer:\n\n{past_text}"))
        result["past_issues_summary"] = past_response.strip()

    return result


@router.get("/tickets/{ticket_id}/summary")
async def get_ticket_summary(
    ticket_id: str,
    force: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-generated summary for a ticket.
    Auto-generates when >5 customer messages. Caches in the ticket document.
    Set force=true to regenerate.
    """
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    customer_msg_count = _count_customer_messages(ticket_id)

    # Check if summary qualifies
    if customer_msg_count < MIN_CUSTOMER_MESSAGES:
        return {
            "eligible": False,
            "customer_message_count": customer_msg_count,
            "min_required": MIN_CUSTOMER_MESSAGES,
            "conversation_summary": None,
            "past_issues_summary": None,
            "past_ticket_count": 0,
        }

    # Check cached summary
    cached = ticket.get("ai_summary")
    if cached and not force:
        cached_msg_count = cached.get("message_count", 0)
        # Stale if 3+ new customer messages since last generation
        if customer_msg_count - cached_msg_count < 3:
            past_tickets = _get_past_tickets_text(ticket.get("customer_email"), ticket_id)
            return {
                "eligible": True,
                "customer_message_count": customer_msg_count,
                "conversation_summary": cached.get("conversation_summary"),
                "past_issues_summary": cached.get("past_issues_summary"),
                "past_ticket_count": len(past_tickets),
                "generated_at": cached.get("generated_at"),
                "cached": True,
            }

    # Generate new summary
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    try:
        conversation_text = _get_conversation_text(ticket_id)
        past_tickets = _get_past_tickets_text(ticket.get("customer_email"), ticket_id)

        summaries = await _generate_summary(api_key, ticket_id, conversation_text, past_tickets)

        # Cache in ticket document
        now = datetime.now(timezone.utc)
        cache_data = {
            "conversation_summary": summaries["conversation_summary"],
            "past_issues_summary": summaries["past_issues_summary"],
            "message_count": customer_msg_count,
            "generated_at": now.isoformat(),
        }
        tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"ai_summary": cache_data, "updated_at": now}}
        )

        return {
            "eligible": True,
            "customer_message_count": customer_msg_count,
            "conversation_summary": summaries["conversation_summary"],
            "past_issues_summary": summaries["past_issues_summary"],
            "past_ticket_count": len(past_tickets),
            "generated_at": now.isoformat(),
            "cached": False,
        }

    except Exception as e:
        logger.error(f"[SUMMARY] Failed to generate summary for {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
