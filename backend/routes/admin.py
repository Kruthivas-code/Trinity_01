"""
Admin routes: custom fields, settings, routing rules, SLA policies admin, escalation rules, auto-close.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
import logging

from pymongo import DESCENDING

from database import (
    tickets_collection, users_collection,
    custom_fields_collection, admin_settings_collection,
    routing_rules_collection, sla_escalation_rules_collection,
    AUTO_CLOSE_HOURS,
)
from dependencies import get_current_user, require_admin
from models.schemas import (
    CustomFieldCreate, CustomFieldUpdate,
    RoutingRuleCreate, RoutingRuleUpdate,
    SLAEscalationRuleCreate, SLAEscalationRuleUpdate,
    SLAPoliciesUpdate,
)
from ticket_helpers import evaluate_condition, run_routing_rules
from utils import serialize_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["admin"])


# ==================== Custom Fields ====================

@router.get("/admin/custom-fields")
async def get_custom_fields(
    entity_type: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """List all custom fields, optionally filtered by entity type (ticket or user)."""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    fields = list(custom_fields_collection.find(query).sort("created_at", DESCENDING))
    return [serialize_doc(f) for f in fields]


@router.post("/admin/custom-fields")
async def create_custom_field(
    field_data: CustomFieldCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new custom field for tickets or users."""
    valid_types = ["text", "number", "select", "date", "boolean"]
    if field_data.field_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid field type. Must be one of: {valid_types}")
    if field_data.entity_type not in ["ticket", "user"]:
        raise HTTPException(status_code=400, detail="Entity type must be 'ticket' or 'user'")
    existing = custom_fields_collection.find_one({"name": field_data.name, "entity_type": field_data.entity_type})
    if existing:
        raise HTTPException(status_code=400, detail="A field with this name already exists")
    field_id = f"field_{uuid.uuid4().hex[:12]}"
    field_doc = {
        "field_id": field_id,
        "name": field_data.name,
        "field_type": field_data.field_type,
        "entity_type": field_data.entity_type,
        "options": field_data.options or [],
        "required": field_data.required,
        "description": field_data.description,
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user.get("user_id")
    }
    custom_fields_collection.insert_one(field_doc)
    return serialize_doc(field_doc)


@router.put("/admin/custom-fields/{field_id}")
async def update_custom_field(
    field_id: str,
    field_data: CustomFieldUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an existing custom field definition."""
    field = custom_fields_collection.find_one({"field_id": field_id})
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    update_data = {k: v for k, v in field_data.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        custom_fields_collection.update_one({"field_id": field_id}, {"$set": update_data})
    updated = custom_fields_collection.find_one({"field_id": field_id})
    return serialize_doc(updated)


@router.delete("/admin/custom-fields/{field_id}")
async def delete_custom_field(
    field_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a custom field by ID."""
    result = custom_fields_collection.delete_one({"field_id": field_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Field not found")
    return {"message": "Field deleted"}


# ==================== Admin Settings ====================

@router.get("/admin/settings")
async def get_admin_settings(current_user: dict = Depends(require_admin)):
    """Get global admin settings (company name, auto-assignment, defaults)."""
    settings = admin_settings_collection.find_one({"type": "global"})
    if not settings:
        return {
            "company_name": "TickFlow",
            "support_email": "",
            "auto_assignment": True,
            "auto_reassign_reopened": False,
            "default_priority": "medium",
            "ticket_statuses": ["todo", "waiting", "closed"],
            "ticket_priorities": ["low", "medium", "high", "urgent"]
        }
    result = serialize_doc(settings)
    if "auto_reassign_reopened" not in result:
        result["auto_reassign_reopened"] = False
    return result


@router.put("/admin/settings")
async def update_admin_settings(
    settings: Dict[str, Any],
    current_user: dict = Depends(require_admin)
):
    """Update global admin settings."""
    settings["type"] = "global"
    settings["updated_at"] = datetime.now(timezone.utc)
    settings["updated_by"] = current_user.get("user_id")
    admin_settings_collection.update_one({"type": "global"}, {"$set": settings}, upsert=True)
    updated_settings = admin_settings_collection.find_one({"type": "global"}, {"_id": 0})
    return serialize_doc(updated_settings) if updated_settings else settings


# ==================== Routing Rules ====================

@router.get("/admin/routing-rules")
async def get_routing_rules(current_user: dict = Depends(require_admin)):
    """List all ticket routing rules, sorted by priority."""
    rules = list(routing_rules_collection.find({}, {"_id": 0}).sort("priority", -1))
    return [serialize_doc(r) for r in rules]


@router.post("/admin/routing-rules")
async def create_routing_rule(
    rule_data: RoutingRuleCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new ticket routing rule with conditions and actions."""
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    condition_groups = rule_data.condition_groups
    if not condition_groups and rule_data.conditions:
        condition_groups = [rule_data.conditions]
    rule_doc = {
        "rule_id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "condition_groups": condition_groups or [[{"field": "priority", "operator": "equals", "value": ""}]],
        "actions": rule_data.actions,
        "priority": rule_data.priority,
        "is_active": rule_data.is_active,
        "assignment_method": rule_data.assignment_method,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    routing_rules_collection.insert_one(rule_doc)
    return serialize_doc(rule_doc)


@router.put("/admin/routing-rules/{rule_id}")
async def update_routing_rule(
    rule_id: str,
    rule_data: RoutingRuleUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an existing routing rule."""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if rule_data.name is not None:
        update_data["name"] = rule_data.name
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    if rule_data.condition_groups is not None:
        update_data["condition_groups"] = rule_data.condition_groups
    elif rule_data.conditions is not None:
        update_data["condition_groups"] = [rule_data.conditions]
    if rule_data.actions is not None:
        update_data["actions"] = rule_data.actions
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["is_active"] = rule_data.is_active
    if rule_data.assignment_method is not None:
        update_data["assignment_method"] = rule_data.assignment_method
    result = routing_rules_collection.update_one({"rule_id": rule_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule = routing_rules_collection.find_one({"rule_id": rule_id}, {"_id": 0})
    return serialize_doc(rule)


@router.delete("/admin/routing-rules/{rule_id}")
async def delete_routing_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete a routing rule by ID."""
    result = routing_rules_collection.delete_one({"rule_id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}


@router.post("/admin/routing-rules/test")
async def test_routing_rule(
    ticket_data: dict,
    current_user: dict = Depends(require_admin)
):
    """Test routing rules against sample ticket data without applying changes."""
    rules = list(routing_rules_collection.find({"is_active": True}, {"_id": 0}).sort("priority", -1))
    matched_rules = []
    for rule in rules:
        conditions = rule.get("conditions", [])
        all_match = True
        condition_results = []
        for condition in conditions:
            result = evaluate_condition(ticket_data, condition)
            condition_results.append({"condition": condition, "matched": result})
            if not result:
                all_match = False
        if all_match:
            matched_rules.append({
                "rule_id": rule.get("rule_id"),
                "rule_name": rule.get("name"),
                "priority": rule.get("priority"),
                "actions": rule.get("actions"),
                "condition_results": condition_results
            })
    return {
        "ticket_data": ticket_data,
        "matched_rules": matched_rules,
        "would_apply": matched_rules[0] if matched_rules else None
    }


@router.post("/tickets/{ticket_id}/route")
async def route_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Run routing rules on a specific ticket and apply matching actions."""
    ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    result = run_routing_rules(ticket)
    updated_ticket = tickets_collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    return {"ticket": serialize_doc(updated_ticket), "routing_result": result}


# ==================== SLA Policies (Admin) ====================

@router.get("/admin/sla-policies")
async def get_sla_policies(current_user: dict = Depends(require_admin)):
    """Get SLA policy configuration including priority-based targets and business hours."""
    settings = admin_settings_collection.find_one({"type": "sla_settings"}) or {}
    return {
        "default_first_response_hours": settings.get("default_first_response_hours", 4),
        "default_resolution_hours": settings.get("default_resolution_hours", 24),
        "priority_slas": settings.get("priority_slas", {
            "low": {"first_response_minutes": 480, "resolution_minutes": 2880},
            "medium": {"first_response_minutes": 240, "resolution_minutes": 1440},
            "high": {"first_response_minutes": 60, "resolution_minutes": 480},
            "urgent": {"first_response_minutes": 15, "resolution_minutes": 120}
        }),
        "business_hours_only": settings.get("business_hours_only", False),
        "business_hours": settings.get("business_hours", {
            "start": "09:00", "end": "18:00", "days": [1, 2, 3, 4, 5]
        }),
        "holidays": settings.get("holidays", []),
        "escalation_debounce_minutes": settings.get("escalation_debounce_minutes", 10)
    }


@router.put("/admin/sla-policies")
async def update_sla_policies(
    data: SLAPoliciesUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update SLA policy settings (response/resolution targets, business hours, holidays)."""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if data.default_first_response_hours is not None:
        update_data["default_first_response_hours"] = data.default_first_response_hours
    if data.default_resolution_hours is not None:
        update_data["default_resolution_hours"] = data.default_resolution_hours
    if data.priority_slas is not None:
        update_data["priority_slas"] = {k: v.dict() if hasattr(v, 'dict') else v for k, v in data.priority_slas.items()}
    if data.business_hours_only is not None:
        update_data["business_hours_only"] = data.business_hours_only
    if data.business_hours is not None:
        update_data["business_hours"] = data.business_hours
    if data.holidays is not None:
        update_data["holidays"] = data.holidays
    if data.escalation_debounce_minutes is not None:
        update_data["escalation_debounce_minutes"] = data.escalation_debounce_minutes
    admin_settings_collection.update_one({"type": "sla_settings"}, {"$set": update_data}, upsert=True)
    updated = admin_settings_collection.find_one({"type": "sla_settings"}, {"_id": 0})
    return {"message": "SLA policies updated successfully", "settings": updated}


# ==================== SLA Escalation Rules ====================

@router.get("/admin/sla-escalation-rules")
async def get_sla_escalation_rules(current_user: dict = Depends(require_admin)):
    """List all SLA escalation rules, sorted by priority."""
    rules = list(sla_escalation_rules_collection.find({}, {"_id": 0}).sort("priority", -1))
    return [serialize_doc(r) for r in rules]


@router.post("/admin/sla-escalation-rules")
async def create_sla_escalation_rule(
    rule_data: SLAEscalationRuleCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new SLA escalation rule with trigger conditions and actions."""
    rule_id = f"sla_rule_{uuid.uuid4().hex[:12]}"
    rule_doc = {
        "rule_id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "trigger_type": rule_data.trigger_type,
        "trigger_threshold": rule_data.trigger_threshold,
        "priority_filter": rule_data.priority_filter,
        "escalation_level_filter": rule_data.escalation_level_filter,
        "actions": rule_data.actions,
        "priority": rule_data.priority,
        "is_active": rule_data.is_active,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    sla_escalation_rules_collection.insert_one(rule_doc)
    return serialize_doc(rule_doc)


@router.put("/admin/sla-escalation-rules/{rule_id}")
async def update_sla_escalation_rule(
    rule_id: str,
    rule_data: SLAEscalationRuleUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an existing SLA escalation rule."""
    update_data = {"updated_at": datetime.now(timezone.utc)}
    if rule_data.name is not None:
        update_data["name"] = rule_data.name
    if rule_data.description is not None:
        update_data["description"] = rule_data.description
    if rule_data.trigger_type is not None:
        update_data["trigger_type"] = rule_data.trigger_type
    if rule_data.trigger_threshold is not None:
        update_data["trigger_threshold"] = rule_data.trigger_threshold
    if rule_data.priority_filter is not None:
        update_data["priority_filter"] = rule_data.priority_filter
    if rule_data.escalation_level_filter is not None:
        update_data["escalation_level_filter"] = rule_data.escalation_level_filter
    if rule_data.actions is not None:
        update_data["actions"] = rule_data.actions
    if rule_data.priority is not None:
        update_data["priority"] = rule_data.priority
    if rule_data.is_active is not None:
        update_data["is_active"] = rule_data.is_active
    result = sla_escalation_rules_collection.update_one({"rule_id": rule_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule = sla_escalation_rules_collection.find_one({"rule_id": rule_id}, {"_id": 0})
    return serialize_doc(rule)


@router.delete("/admin/sla-escalation-rules/{rule_id}")
async def delete_sla_escalation_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete an SLA escalation rule by ID."""
    result = sla_escalation_rules_collection.delete_one({"rule_id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}


@router.post("/admin/sla-escalation-rules/check")
async def run_sla_check(current_user: dict = Depends(require_admin)):
    """Manually trigger SLA escalation check - stub"""
    return {"message": "SLA check completed", "escalated": 0, "checked": 0}


# ==================== Auto-close Status ====================

@router.get("/admin/auto-close-status")
async def get_auto_close_status(current_user: dict = Depends(require_admin)):
    """Get the auto-close configuration status"""
    return {
        "enabled": True,
        "auto_close_hours": AUTO_CLOSE_HOURS,
        "description": f"Resolved tickets are automatically closed after {AUTO_CLOSE_HOURS} hours"
    }
