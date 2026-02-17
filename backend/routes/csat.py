"""
Routes for csat.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import secrets
import hashlib
import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Query
from pymongo import DESCENDING
from database import (
    db, csat_responses_collection, csat_tokens_collection,
    tickets_collection, users_collection,
)
from dependencies import get_current_user
from models.schemas import CSATRequest, CSATFeedbackRequest, CSATRatingRequest
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["csat"])

# ==================== CSAT (Customer Satisfaction) System ====================

# Generate secure token for CSAT email links
def generate_csat_token(ticket_id: str, customer_email: str) -> str:
    """Generate a secure, unique token for CSAT rating links"""
    random_part = secrets.token_urlsafe(32)
    return f"csat_{hashlib.sha256(f'{ticket_id}:{customer_email}:{random_part}'.encode()).hexdigest()[:24]}"

@router.post("/csat/send/{ticket_id}")
async def send_csat_survey(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate CSAT survey for a resolved ticket (email is MOCKED)"""
    # Get ticket
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_email = ticket.get("customer_email")
    if not customer_email:
        raise HTTPException(status_code=400, detail="Ticket has no customer email")
    
    # Check if CSAT already sent
    existing = csat_tokens_collection.find_one({"ticket_id": ticket_id})
    if existing:
        return {
            "message": "CSAT survey already sent for this ticket",
            "token": existing.get("token"),
            "sent_at": existing.get("created_at"),
            "already_sent": True
        }
    
    # Generate token
    token = generate_csat_token(ticket_id, customer_email)
    
    # Store token
    token_doc = {
        "token": token,
        "ticket_id": ticket_id,
        "customer_email": customer_email,
        "customer_name": ticket.get("customer_name") or customer_email.split("@")[0],
        "ticket_title": ticket.get("title"),
        "resolved_by": ticket.get("assignee_id"),
        "resolved_by_name": None,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "used": False,
        "used_at": None
    }
    
    # Get resolver name
    if ticket.get("assignee_id"):
        resolver = users_collection.find_one({"user_id": ticket["assignee_id"]}, {"_id": 0, "name": 1})
        if resolver:
            token_doc["resolved_by_name"] = resolver.get("name")
    
    csat_tokens_collection.insert_one(token_doc)
    
    # Generate email content (MOCKED - not actually sent)
    base_url = os.environ.get("CSAT_BASE_URL", os.environ.get("ALLOWED_ORIGINS", "https://ticket-ai-system-1.preview.emergentagent.com").split(",")[0].strip())
    
    email_content = {
        "to": customer_email,
        "subject": f"How was your experience? - {ticket.get('title', 'Your request')}",
        "html": f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rate Your Experience</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <tr>
            <td style="padding: 40px 30px; text-align: center; background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">✅ Your ticket has been resolved</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 30px;">
                <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px;">
                    Hi {token_doc['customer_name']},
                </p>
                <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 20px;">
                    Your request has been resolved:
                </p>
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                    <p style="color: #6b7280; font-size: 14px; margin: 0 0 5px;">Ticket #{ticket_id}</p>
                    <p style="color: #111827; font-size: 18px; font-weight: 600; margin: 0;">{ticket.get('title', 'Support Request')}</p>
                    {f'<p style="color: #6b7280; font-size: 14px; margin: 10px 0 0;">Resolved by: {token_doc["resolved_by_name"]}</p>' if token_doc.get("resolved_by_name") else ''}
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <p style="color: #374151; font-size: 18px; font-weight: 600; margin: 0 0 20px;">How was your experience?</p>
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="text-align: center;">
                                <a href="{base_url}/csat/{token}?rating=1" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Terrible</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=2" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Poor</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=3" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Okay</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=4" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Good</span>
                                </a>
                                <a href="{base_url}/csat/{token}?rating=5" style="display: inline-block; text-decoration: none; margin: 0 8px;">
                                    <span style="font-size: 36px;">⭐⭐⭐⭐⭐</span>
                                    <br><span style="color: #6b7280; font-size: 12px;">Excellent</span>
                                </a>
                            </td>
                        </tr>
                    </table>
                    <p style="color: #9ca3af; font-size: 14px; margin: 20px 0 0;">Click a star rating - takes just 1 second!</p>
                </div>
            </td>
        </tr>
        <tr>
            <td style="padding: 20px 30px; background-color: #f9fafb; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This survey expires in 7 days. Your feedback helps us improve.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
        """,
        "text": f"""
Your ticket has been resolved!

Hi {token_doc['customer_name']},

Your support request has been resolved:
Ticket #{ticket_id}: {ticket.get('title', 'Support Request')}
{f"Resolved by: {token_doc['resolved_by_name']}" if token_doc.get("resolved_by_name") else ""}

How was your experience? Click a rating:

⭐ Terrible: {base_url}/csat/{token}?rating=1
⭐⭐ Poor: {base_url}/csat/{token}?rating=2  
⭐⭐⭐ Okay: {base_url}/csat/{token}?rating=3
⭐⭐⭐⭐ Good: {base_url}/csat/{token}?rating=4
⭐⭐⭐⭐⭐ Excellent: {base_url}/csat/{token}?rating=5

This survey expires in 7 days.
        """
    }
    
    # Email sending is pending provider configuration
    # For now, return the survey link that can be shared manually
    logger.info(f"[CSAT] Survey created for ticket {ticket_id}, token: {token}")
    
    return {
        "message": "CSAT survey created. Email delivery pending provider configuration.",
        "token": token,
        "rating_url_template": f"{base_url}/csat/{token}?rating={{rating}}",
        "expires_at": token_doc["expires_at"],
    }


@router.get("/csat/check/{token}")
async def check_csat_status(token: str):
    """Check CSAT token status (no auth required) - safe for GET/prefetch"""
    # Find token
    token_doc = csat_tokens_collection.find_one({"token": token})
    if not token_doc:
        raise HTTPException(status_code=404, detail="Invalid or expired survey link")
    
    # Check expiration
    expires_at = token_doc.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="This survey link has expired")
    
    # Check if already responded
    existing_response = csat_responses_collection.find_one({"token": token})
    if existing_response:
        return {
            "status": "already_submitted",
            "rating": existing_response.get("rating"),
            "ticket_id": token_doc.get("ticket_id"),
            "customer_name": token_doc.get("customer_name"),
            "ticket_title": token_doc.get("ticket_title")
        }
    
    return {
        "status": "pending",
        "ticket_id": token_doc.get("ticket_id"),
        "customer_name": token_doc.get("customer_name"),
        "ticket_title": token_doc.get("ticket_title")
    }


@router.post("/csat/rate/{token}")
async def submit_csat_rating(
    token: str,
    request: CSATRatingRequest
):
    """Handle CSAT rating submission (POST to prevent email prefetch attacks)"""
    rating = request.rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Find token
    token_doc = csat_tokens_collection.find_one({"token": token})
    if not token_doc:
        raise HTTPException(status_code=404, detail="Invalid or expired survey link")
    
    # Check expiration
    expires_at = token_doc.get("expires_at")
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="This survey link has expired")
    
    # Check if already responded
    existing_response = csat_responses_collection.find_one({"token": token})
    if existing_response:
        return {
            "message": "You have already submitted a rating for this ticket",
            "rating": existing_response.get("rating"),
            "already_submitted": True,
            "ticket_id": token_doc.get("ticket_id")
        }
    
    # Create CSAT response
    response_id = f"csat_{uuid.uuid4().hex[:12]}"
    csat_doc = {
        "response_id": response_id,
        "token": token,
        "ticket_id": token_doc.get("ticket_id"),
        "customer_email": token_doc.get("customer_email"),
        "customer_name": token_doc.get("customer_name"),
        "rating": rating,
        "feedback": None,
        "was_resolved": None,
        "resolved_by": token_doc.get("resolved_by"),
        "resolved_by_name": token_doc.get("resolved_by_name"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    csat_responses_collection.insert_one(csat_doc)
    
    # Mark token as used
    csat_tokens_collection.update_one(
        {"token": token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
    )
    
    # Update ticket with CSAT score
    tickets_collection.update_one(
        {"ticket_id": token_doc.get("ticket_id")},
        {"$set": {
            "csat_score": rating,
            "csat_response_id": response_id,
            "csat_submitted_at": datetime.now(timezone.utc)
        }}
    )
    
    # If low rating (≤2), create alert notification for manager
    if rating <= 2:
        alert_doc = {
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "type": "low_csat_alert",
            "ticket_id": token_doc.get("ticket_id"),
            "customer_email": token_doc.get("customer_email"),
            "rating": rating,
            "resolved_by": token_doc.get("resolved_by"),
            "resolved_by_name": token_doc.get("resolved_by_name"),
            "created_at": datetime.now(timezone.utc),
            "read": False,
            "message": f"Low CSAT rating ({rating}/5) received for ticket {token_doc.get('ticket_id')} from {token_doc.get('customer_email')}"
        }
        # Store in a notifications collection (or could be sent via WebSocket)
        db.notifications.insert_one(alert_doc)
        logger.warning(f"[LOW CSAT ALERT] Rating {rating}/5 for ticket {token_doc.get('ticket_id')} - Manager notified")
    
    return {
        "message": "Thank you for your feedback!",
        "response_id": response_id,
        "rating": rating,
        "ticket_id": token_doc.get("ticket_id"),
        "can_add_feedback": True
    }


@router.post("/csat/{response_id}/feedback")
async def add_csat_feedback(
    response_id: str,
    request: CSATFeedbackRequest
):
    """Add optional feedback to CSAT response (no auth required)"""
    # Find response
    response = csat_responses_collection.find_one({"response_id": response_id})
    if not response:
        raise HTTPException(status_code=404, detail="CSAT response not found")
    
    # Update with feedback
    update_fields = {"updated_at": datetime.now(timezone.utc)}
    if request.feedback:
        update_fields["feedback"] = request.feedback
    if request.was_resolved is not None:
        update_fields["was_resolved"] = request.was_resolved
    
    csat_responses_collection.update_one(
        {"response_id": response_id},
        {"$set": update_fields}
    )
    
    # Also update ticket if feedback provided
    if request.feedback:
        tickets_collection.update_one(
            {"ticket_id": response.get("ticket_id")},
            {"$set": {"csat_feedback": request.feedback}}
        )
    
    return {
        "message": "Feedback submitted successfully",
        "response_id": response_id
    }


@router.get("/csat/ticket/{ticket_id}")
async def get_ticket_csat(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get CSAT data for a specific ticket"""
    # Check for response
    response = csat_responses_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0}
    )
    
    # Check for pending token
    token = csat_tokens_collection.find_one(
        {"ticket_id": ticket_id},
        {"_id": 0, "token": 0}  # Don't expose token
    )
    
    if response:
        return {
            "has_response": True,
            "rating": response.get("rating"),
            "feedback": response.get("feedback"),
            "was_resolved": response.get("was_resolved"),
            "submitted_at": response.get("created_at"),
            "customer_name": response.get("customer_name")
        }
    elif token:
        return {
            "has_response": False,
            "survey_sent": True,
            "sent_at": token.get("created_at"),
            "expires_at": token.get("expires_at"),
            "used": token.get("used", False)
        }
    else:
        return {
            "has_response": False,
            "survey_sent": False
        }


@router.get("/csat/analytics")
async def get_csat_analytics(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get CSAT analytics and metrics"""
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all responses in period
    responses = list(csat_responses_collection.find(
        {"created_at": {"$gte": from_date}},
        {"_id": 0}
    ))
    
    if not responses:
        return {
            "period_days": days,
            "total_responses": 0,
            "average_rating": None,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "satisfaction_rate": None,
            "low_ratings": [],
            "by_agent": []
        }
    
    # Calculate metrics
    total = len(responses)
    ratings = [r.get("rating", 0) for r in responses]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Rating distribution
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r in distribution:
            distribution[r] += 1
    
    # Satisfaction rate (4 or 5 stars)
    satisfied = len([r for r in ratings if r >= 4])
    satisfaction_rate = (satisfied / total * 100) if total > 0 else 0
    
    # Low ratings (≤2) with details
    low_ratings = [
        {
            "ticket_id": r.get("ticket_id"),
            "rating": r.get("rating"),
            "feedback": r.get("feedback"),
            "customer_email": r.get("customer_email"),
            "resolved_by_name": r.get("resolved_by_name"),
            "created_at": r.get("created_at")
        }
        for r in responses if r.get("rating", 5) <= 2
    ]
    
    # By agent
    agent_ratings = {}
    for r in responses:
        agent_id = r.get("resolved_by")
        if agent_id:
            if agent_id not in agent_ratings:
                agent_ratings[agent_id] = {
                    "user_id": agent_id,
                    "name": r.get("resolved_by_name", "Unknown"),
                    "ratings": [],
                    "count": 0
                }
            agent_ratings[agent_id]["ratings"].append(r.get("rating", 0))
            agent_ratings[agent_id]["count"] += 1
    
    by_agent = []
    for agent in agent_ratings.values():
        avg = sum(agent["ratings"]) / len(agent["ratings"]) if agent["ratings"] else 0
        by_agent.append({
            "user_id": agent["user_id"],
            "name": agent["name"],
            "response_count": agent["count"],
            "average_rating": round(avg, 2)
        })
    
    by_agent.sort(key=lambda x: -x["average_rating"])
    
    return {
        "period_days": days,
        "total_responses": total,
        "average_rating": round(avg_rating, 2),
        "rating_distribution": distribution,
        "satisfaction_rate": round(satisfaction_rate, 1),
        "low_ratings": low_ratings[:10],
        "by_agent": by_agent
    }


