"""
Recurring background job: sweeps unassigned open tickets and assigns them
using routing rules + fallback assignment method.

Runs every SWEEP_INTERVAL_SECONDS. Skips Zeus-handled tickets.
"""
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from database import (
    tickets_collection, admin_settings_collection, teams_collection,
)
from ticket_helpers import run_routing_rules, assign_by_method

logger = logging.getLogger("ticket_sweep")

SWEEP_INTERVAL_SECONDS = 300  # 5 minutes
TICKET_AGE_THRESHOLD_MINUTES = 10  # Only sweep tickets older than this

_stop_event = threading.Event()


def _get_settings() -> dict:
    return admin_settings_collection.find_one({"type": "global"}, {"_id": 0}) or {}


def _get_default_team_id() -> str | None:
    """Get the default team for fallback assignment (first team with members)."""
    settings = _get_settings()
    default_team = settings.get("default_team_id")
    if default_team:
        team = teams_collection.find_one({"team_id": default_team, "members.0": {"$exists": True}})
        if team:
            return default_team

    # Fallback: find any team with members
    team = teams_collection.find_one({"members.0": {"$exists": True}}, {"_id": 0, "team_id": 1})
    return team.get("team_id") if team else None


def sweep_unassigned_tickets() -> dict:
    """
    Find and assign unassigned open tickets.
    1. Skip Zeus-handled tickets
    2. Run routing rules first (may assign via rule)
    3. If still unassigned, fallback to default team + assignment method
    Returns stats dict.
    """
    settings = _get_settings()
    if not settings.get("auto_assignment", False):
        return {"skipped": True, "reason": "auto_assignment disabled"}

    assignment_method = settings.get("assignment_method", "round_robin")
    age_threshold = datetime.now(timezone.utc) - timedelta(minutes=TICKET_AGE_THRESHOLD_MINUTES)

    # Find unassigned, non-Zeus, open tickets older than threshold
    query = {
        "status": {"$in": ["todo", "in_progress", "waiting"]},
        "assignee_id": None,
        "atlas_assigned_to_zeus": {"$ne": True},
        "created_at": {"$lt": age_threshold},
    }

    unassigned = list(tickets_collection.find(
        query,
        {"_id": 0, "ticket_id": 1, "team_id": 1, "status": 1, "priority": 1,
         "escalation_level": 1, "tags": 1, "customer_email": 1, "domain": 1, "source": 1}
    ).sort("created_at", 1).limit(50))  # Process oldest first, batch of 50

    if not unassigned:
        return {"checked": 0, "assigned": 0}

    assigned_count = 0
    routing_matched = 0
    fallback_assigned = 0

    for ticket in unassigned:
        ticket_id = ticket["ticket_id"]

        # Step 1: Try routing rules
        result = run_routing_rules(ticket)
        if result.get("matched"):
            routing_matched += 1
            # Check if routing actually assigned someone
            updated = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0, "assignee_id": 1})
            if updated and updated.get("assignee_id"):
                assigned_count += 1
                continue

        # Step 2: Still unassigned — try team-based assignment
        team_id = ticket.get("team_id")
        if not team_id:
            team_id = _get_default_team_id()
            if team_id:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$set": {"team_id": team_id}}
                )

        if team_id:
            assignee = assign_by_method(team_id, assignment_method)
            if assignee:
                tickets_collection.update_one(
                    {"ticket_id": ticket_id},
                    {"$set": {
                        "assignee_id": assignee,
                        "updated_at": datetime.now(timezone.utc),
                    }}
                )
                assigned_count += 1
                fallback_assigned += 1

    return {
        "checked": len(unassigned),
        "assigned": assigned_count,
        "routing_matched": routing_matched,
        "fallback_assigned": fallback_assigned,
    }


def _sweep_loop():
    """Background loop that runs the sweep periodically."""
    logger.info(f"[SWEEP] Ticket sweep daemon started (interval={SWEEP_INTERVAL_SECONDS}s)")
    while not _stop_event.is_set():
        try:
            stats = sweep_unassigned_tickets()
            if stats.get("skipped"):
                logger.debug(f"[SWEEP] Skipped: {stats.get('reason')}")
            elif stats.get("assigned", 0) > 0:
                logger.info(f"[SWEEP] Assigned {stats['assigned']}/{stats['checked']} tickets "
                           f"(routing={stats.get('routing_matched',0)}, fallback={stats.get('fallback_assigned',0)})")
        except Exception as e:
            logger.error(f"[SWEEP] Error: {e}")

        _stop_event.wait(SWEEP_INTERVAL_SECONDS)


def start_sweep():
    """Start the sweep daemon in a background thread."""
    _stop_event.clear()
    t = threading.Thread(target=_sweep_loop, daemon=True, name="ticket-sweep")
    t.start()
    return t


def stop_sweep():
    """Signal the sweep daemon to stop."""
    _stop_event.set()
