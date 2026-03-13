"""
Ticket routing, assignment, and shift-based helper functions.
These are shared across multiple route modules.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from database import (
    tickets_collection, users_collection, teams_collection,
    shifts_collection, user_shifts_collection,
    routing_rules_collection, admin_settings_collection,
)
from utils import get_ist_now, parse_time_str

logger = logging.getLogger(__name__)


def evaluate_condition(ticket: dict, condition: dict) -> bool:
    """Evaluate a single routing rule condition against a ticket"""
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    value = condition.get("value", "")

    ticket_value = ticket.get(field)

    if operator == "equals":
        return str(ticket_value).lower() == str(value).lower()
    elif operator == "not_equals":
        return str(ticket_value).lower() != str(value).lower()
    elif operator == "contains":
        return str(value).lower() in str(ticket_value or "").lower()
    elif operator == "not_contains":
        return str(value).lower() not in str(ticket_value or "").lower()
    elif operator == "in":
        if isinstance(value, list):
            return ticket_value in value
        return ticket_value in [v.strip() for v in str(value).split(",")]
    elif operator == "exists":
        return ticket_value is not None and ticket_value != ""
    elif operator == "not_exists":
        return ticket_value is None or ticket_value == ""
    return False


def run_routing_rules(ticket: dict) -> dict:
    """Run routing rules against a ticket and apply first matching rule"""
    rules = list(routing_rules_collection.find(
        {"is_active": True},
        {"_id": 0}
    ).sort("priority", -1))

    for rule in rules:
        condition_groups = rule.get("condition_groups", [])
        if not condition_groups:
            conditions = rule.get("conditions", [])
            condition_groups = [conditions] if conditions else []

        matched = False
        for group in condition_groups:
            group_match = all(evaluate_condition(ticket, c) for c in group) if group else False
            if group_match:
                matched = True
                break

        if matched:
            actions = rule.get("actions", {})
            update_data = {}
            assignment_method = rule.get("assignment_method", "round_robin")

            if actions.get("assign_team"):
                update_data["team_id"] = actions["assign_team"]
                # Auto-assign an agent from this team if no specific user is set
                if not actions.get("assign_user"):
                    assignee = assign_by_method(actions["assign_team"], assignment_method)
                    if assignee:
                        update_data["assignee_id"] = assignee
            if actions.get("assign_user"):
                update_data["assignee_id"] = actions["assign_user"]
            if actions.get("set_priority"):
                update_data["priority"] = actions["set_priority"]
            if actions.get("set_escalation_level"):
                update_data["escalation_level"] = actions["set_escalation_level"]
            if actions.get("add_tags"):
                tags = actions["add_tags"]
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",")]
                tickets_collection.update_one(
                    {"ticket_id": ticket.get("ticket_id")},
                    {"$addToSet": {"tags": {"$each": tags}}}
                )

            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                tickets_collection.update_one(
                    {"ticket_id": ticket.get("ticket_id")},
                    {"$set": update_data}
                )

            return {
                "matched": True,
                "rule_name": rule.get("name"),
                "rule_id": rule.get("rule_id"),
                "actions_applied": update_data
            }

    return {"matched": False}


def get_available_agents(team_id: str) -> List[dict]:
    """Get available agents in a team for assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team or not team.get("members"):
        return []

    agents = list(users_collection.find({
        "user_id": {"$in": team["members"]},
        "status": {"$ne": "offline"},
        "on_leave": {"$ne": True}
    }))

    available = []
    for agent in agents:
        current_count = tickets_collection.count_documents({
            "assignee_id": agent["user_id"],
            "status": {"$nin": ["closed"]}
        })
        max_tickets = agent.get("max_tickets", 10)
        if current_count < max_tickets:
            agent["current_ticket_count"] = current_count
            available.append(agent)

    return available


def round_robin_assign(team_id: str) -> Optional[str]:
    """Get next agent for round-robin assignment"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        return None

    available = get_available_agents(team_id)
    if not available:
        return None

    last_idx = team.get("last_assigned_idx", -1)
    member_ids = [a["user_id"] for a in available]
    all_members = team.get("members", [])

    for i in range(len(all_members)):
        idx = (last_idx + 1 + i) % len(all_members)
        member_id = all_members[idx]

        if member_id in member_ids:
            teams_collection.update_one(
                {"team_id": team_id},
                {"$set": {"last_assigned_idx": idx}}
            )
            return member_id

    return None


def least_tickets_assign(team_id: str) -> Optional[str]:
    """Assign to the agent with fewest open tickets in the team."""
    available = get_available_agents(team_id)
    if not available:
        return None
    # Sort by current_ticket_count ascending (set in get_available_agents)
    available.sort(key=lambda a: a.get("current_ticket_count", 0))
    return available[0]["user_id"]


def assign_by_method(team_id: str, method: str = "round_robin") -> Optional[str]:
    """Assign an agent using the specified method. Falls back to round_robin."""
    if method == "least_tickets":
        return least_tickets_assign(team_id)
    return round_robin_assign(team_id)


def auto_assign_on_escalation(ticket_id: str, new_level: str) -> dict:
    """Auto-assign ticket based on escalation level"""
    target_team = teams_collection.find_one(
        {"escalation_level": new_level},
        {"_id": 0}
    )

    if not target_team:
        return {"assigned": False, "reason": f"No team found for level {new_level}"}

    team_id = target_team.get("team_id")
    settings = admin_settings_collection.find_one({"type": "global"}, {"_id": 0}) or {}
    method = settings.get("assignment_method", "round_robin")
    assignee_id = assign_by_method(team_id, method)

    update_data = {
        "escalation_level": new_level,
        "team_id": team_id,
        "updated_at": datetime.now(timezone.utc)
    }
    if assignee_id:
        update_data["assignee_id"] = assignee_id

    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": update_data}
    )

    return {
        "assigned": bool(assignee_id),
        "team_id": team_id,
        "team_name": target_team.get("name"),
        "assignee_id": assignee_id
    }


def handle_ticket_reopen_reassignment(ticket: dict, new_status: str, changed_by: str) -> Optional[dict]:
    """Handle auto-reassignment when a ticket is reopened from closed"""
    old_status = ticket.get("status")

    if old_status not in ("closed",) or new_status in ("closed", "merged"):
        return None

    settings = admin_settings_collection.find_one({}, {"_id": 0}) or {}
    if not settings.get("auto_reassign_on_reopen", False):
        return None

    old_assignee_id = ticket.get("assignee_id")
    if not old_assignee_id:
        return None

    old_assignee = users_collection.find_one({"user_id": old_assignee_id}, {"_id": 0})
    old_assignee_name = old_assignee.get("name", "Unknown") if old_assignee else "Unknown"

    team_id = ticket.get("team_id")
    if team_id:
        from routes.shifts import is_user_on_shift
        if is_user_on_shift(old_assignee_id, team_id):
            return {"reassigned": False, "reason": "original_assignee_on_shift"}

        new_assignee = round_robin_assign(team_id)
        if new_assignee:
            new_user = users_collection.find_one({"user_id": new_assignee}, {"_id": 0})
            return {
                "reassigned": True,
                "old_assignee_id": old_assignee_id,
                "old_assignee_name": old_assignee_name,
                "new_assignee_id": new_assignee,
                "new_assignee_name": new_user.get("name", "Unknown") if new_user else "Unknown",
                "reason": "original_assignee_off_shift"
            }

    return {
        "reassigned": True,
        "old_assignee_id": old_assignee_id,
        "old_assignee_name": old_assignee_name,
        "new_assignee_id": None,
        "new_assignee_name": None,
        "reason": "no_agents_on_shift"
    }


def trigger_shift_start_assignment(user_id: str) -> list:
    """Assign queued/unassigned tickets when a user starts their shift"""
    settings = admin_settings_collection.find_one({}, {"_id": 0}) or {}
    if not settings.get("auto_assignment", False):
        return []

    user = users_collection.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        return []

    team_id = user.get("team_id")
    if not team_id:
        return []

    queued_tickets = list(tickets_collection.find({
        "team_id": team_id,
        "status": "todo",
        "$or": [
            {"assignee_id": None},
            {"assignee_id": {"$exists": False}}
        ]
    }, {"_id": 0}).sort("created_at", 1).limit(5))

    assigned = []
    for ticket in queued_tickets:
        current_count = tickets_collection.count_documents({
            "assignee_id": user_id,
            "status": {"$nin": ["closed"]}
        })
        max_tickets = user.get("max_tickets", 10)
        if current_count >= max_tickets:
            break

        tickets_collection.update_one(
            {"ticket_id": ticket["ticket_id"]},
            {"$set": {
                "assignee_id": user_id,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        assigned.append(ticket["ticket_id"])

    return assigned
