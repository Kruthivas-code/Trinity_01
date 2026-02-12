"""
All Pydantic request/response models for the Trinity API.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any

from database import (
    VALID_STATUSES, VALID_PRIORITIES, VALID_ESCALATION_LEVELS, VALID_SOURCES,
    MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_TAGS, MAX_TAG_LENGTH,
    MAX_CUSTOM_FIELD_VALUE_LENGTH, WEBHOOK_EVENT_TYPES,
)


# ==================== Auth ====================

class SessionCreate(BaseModel):
    session_id: str = Field(..., min_length=10, max_length=500)

    model_config = {"json_schema_extra": {"examples": [{"session_id": "abc123def456ghi789jkl012mno345pqr"}]}}


# ==================== Tickets ====================

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=MAX_TITLE_LENGTH)
    description: Optional[str] = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)
    status: str = Field(default="todo")
    assignee_id: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[str] = Field(default="medium")
    tags: Optional[List[str]] = Field(default=[])
    customer_email: Optional[EmailStr] = None
    source: Optional[str] = Field(default="manual")
    escalation_level: Optional[str] = Field(default="L1")

    model_config = {"json_schema_extra": {"examples": [{"title": "Login page returns 500 error", "description": "Users see a 500 error when clicking Sign In with Google on the login page.", "status": "todo", "priority": "high", "tags": ["bug", "auth"], "customer_email": "jane@acme.com", "source": "manual", "escalation_level": "L1"}]}}

    @validator('status')
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f'Status must be one of: {", ".join(VALID_STATUSES)}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in VALID_PRIORITIES:
            raise ValueError(f'Priority must be one of: {", ".join(VALID_PRIORITIES)}')
        return v

    @validator('escalation_level')
    def validate_escalation(cls, v):
        if v and v not in VALID_ESCALATION_LEVELS:
            raise ValueError(f'Escalation level must be one of: {", ".join(VALID_ESCALATION_LEVELS)}')
        return v

    @validator('source')
    def validate_source(cls, v):
        if v and v not in VALID_SOURCES:
            raise ValueError(f'Source must be one of: {", ".join(VALID_SOURCES)}')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v:
            if len(v) > MAX_TAGS:
                raise ValueError(f'Maximum {MAX_TAGS} tags allowed')
            for tag in v:
                if len(tag) > MAX_TAG_LENGTH:
                    raise ValueError(f'Tag length cannot exceed {MAX_TAG_LENGTH} characters')
        return v


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=MAX_TITLE_LENGTH)
    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    status: Optional[str] = None
    assignee_id: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    escalation_level: Optional[str] = None
    team_id: Optional[str] = Field(default=None, max_length=100)
    is_starred: Optional[bool] = None
    snoozed: Optional[bool] = None

    model_config = {"json_schema_extra": {"examples": [{"status": "in_progress", "priority": "urgent", "assignee_id": "user_abc123", "tags": ["bug", "auth", "critical"]}]}}

    @validator('status')
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f'Status must be one of: {", ".join(VALID_STATUSES)}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v and v not in VALID_PRIORITIES:
            raise ValueError(f'Priority must be one of: {", ".join(VALID_PRIORITIES)}')
        return v

    @validator('escalation_level')
    def validate_escalation(cls, v):
        if v and v not in VALID_ESCALATION_LEVELS:
            raise ValueError(f'Escalation level must be one of: {", ".join(VALID_ESCALATION_LEVELS)}')
        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v:
            if len(v) > MAX_TAGS:
                raise ValueError(f'Maximum {MAX_TAGS} tags allowed')
            for tag in v:
                if len(tag) > MAX_TAG_LENGTH:
                    raise ValueError(f'Tag length cannot exceed {MAX_TAG_LENGTH} characters')
        return v

    @validator('custom_fields')
    def validate_custom_fields(cls, v):
        if v:
            for key, value in v.items():
                if isinstance(value, str) and len(value) > MAX_CUSTOM_FIELD_VALUE_LENGTH:
                    raise ValueError(f'Custom field value cannot exceed {MAX_CUSTOM_FIELD_VALUE_LENGTH} characters')
        return v


class TicketReorder(BaseModel):
    ticket_id: str
    new_status: str
    new_order: int

    model_config = {"json_schema_extra": {"examples": [{"ticket_id": "TKT-00042", "new_status": "in_progress", "new_order": 2}]}}


class TicketAssign(BaseModel):
    assignee_id: Optional[str] = None
    team_id: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [{"assignee_id": "user_abc123", "team_id": "team_support01"}]}}


class TicketEscalate(BaseModel):
    escalation_level: str  # L1, L2, L3
    reason: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [{"escalation_level": "L2", "reason": "Customer is a VIP and issue is unresolved for 48 hours"}]}}


class InternalNoteCreate(BaseModel):
    content: str
    mentions: Optional[List[str]] = []
    type: Optional[str] = "internal_note"

    model_config = {"json_schema_extra": {"examples": [{"content": "Checked logs — this is caused by the OAuth redirect URI mismatch. @user_jsmith can you update the config?", "mentions": ["user_jsmith"], "type": "internal_note"}]}}


class BulkUpdateRequest(BaseModel):
    ticket_ids: List[str]
    updates: dict

    model_config = {"json_schema_extra": {"examples": [{"ticket_ids": ["TKT-00042", "TKT-00043", "TKT-00044"], "updates": {"status": "in_progress", "assignee_id": "user_abc123"}}]}}


class BulkTagRequest(BaseModel):
    ticket_ids: List[str]
    tags_to_add: List[str] = []
    tags_to_remove: List[str] = []

    model_config = {"json_schema_extra": {"examples": [{"ticket_ids": ["TKT-00042", "TKT-00043"], "tags_to_add": ["priority-review", "q1-sprint"], "tags_to_remove": ["backlog"]}]}}


# ==================== Users ====================

class UserPreferences(BaseModel):
    theme: Optional[str] = "dark"

    model_config = {"json_schema_extra": {"examples": [{"theme": "dark"}]}}


class UserRoleUpdate(BaseModel):
    role: str
    team_id: Optional[str] = None
    skills: Optional[List[str]] = None
    max_tickets: Optional[int] = 10

    model_config = {"json_schema_extra": {"examples": [{"role": "agent", "team_id": "team_support01", "skills": ["billing", "technical"], "max_tickets": 15}]}}


# ==================== API Keys ====================

class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = ""

    model_config = {"json_schema_extra": {"examples": [{"name": "CI/CD Pipeline Key", "description": "Used by GitHub Actions for automated ticket creation"}]}}


class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    key: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None


# ==================== Teams ====================

class TeamCreate(BaseModel):
    name: str
    escalation_level: str = "L1"
    description: Optional[str] = ""

    model_config = {"json_schema_extra": {"examples": [{"name": "Tier 1 Support", "escalation_level": "L1", "description": "Frontline support handling initial customer inquiries"}]}}


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    escalation_level: Optional[str] = None
    description: Optional[str] = None
    lead_id: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [{"name": "Tier 2 Engineering", "escalation_level": "L2", "lead_id": "user_jsmith"}]}}


class TeamMemberAdd(BaseModel):
    user_id: str

    model_config = {"json_schema_extra": {"examples": [{"user_id": "user_abc123"}]}}


# ==================== Shifts ====================

class ShiftCreate(BaseModel):
    team_id: str
    name: str
    start_time: str
    end_time: str
    days_of_week: List[int] = [1, 2, 3, 4, 5]

    model_config = {"json_schema_extra": {"examples": [{"team_id": "team_support01", "name": "Morning Shift", "start_time": "09:00", "end_time": "17:00", "days_of_week": [1, 2, 3, 4, 5]}]}}


class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    is_active: Optional[bool] = None

    model_config = {"json_schema_extra": {"examples": [{"name": "Evening Shift", "start_time": "17:00", "end_time": "01:00", "days_of_week": [1, 2, 3, 4, 5, 6]}]}}


class UserShiftAssign(BaseModel):
    shift_id: str
    is_primary: bool = True
    effective_from: Optional[str] = None

    model_config = {"json_schema_extra": {"examples": [{"shift_id": "shift_morning01", "is_primary": True, "effective_from": "2026-02-15"}]}}


# ==================== Routing Rules ====================

class RoutingRuleCondition(BaseModel):
    field: str
    operator: str
    value: Any


class RoutingRuleAction(BaseModel):
    type: str
    value: str


class RoutingRuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    condition_groups: Optional[List[List[Dict[str, Any]]]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: List[Dict[str, Any]]
    priority: int = 0
    is_active: bool = True
    assignment_method: str = "round_robin"


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_groups: Optional[List[List[Dict[str, Any]]]] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    assignment_method: Optional[str] = None


# ==================== SLA Escalation Rules ====================

class SLAEscalationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    trigger_type: str = Field(..., pattern="^(first_response_warning|first_response_breach|resolution_warning|resolution_breach|idle_ticket)$")
    trigger_threshold: int = Field(ge=1, le=10000)
    priority_filter: Optional[List[str]] = None
    escalation_level_filter: Optional[List[str]] = None
    actions: List[Dict[str, Any]] = Field(min_length=1)
    priority: int = Field(default=0, ge=0, le=1000)
    is_active: bool = True


class SLAEscalationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_threshold: Optional[int] = None
    priority_filter: Optional[List[str]] = None
    escalation_level_filter: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


# ==================== SLA Policies ====================

class SLAPolicyPriority(BaseModel):
    first_response_minutes: int = Field(ge=1)
    resolution_minutes: int = Field(ge=1)


class SLAPoliciesUpdate(BaseModel):
    default_first_response_hours: Optional[int] = Field(None, ge=1, le=168)
    default_resolution_hours: Optional[int] = Field(None, ge=1, le=720)
    priority_slas: Optional[Dict[str, SLAPolicyPriority]] = None
    business_hours_only: Optional[bool] = None
    business_hours: Optional[Dict[str, Any]] = None
    holidays: Optional[List[str]] = None
    escalation_debounce_minutes: Optional[int] = Field(None, ge=1, le=1440)


class SLAPolicy(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str
    first_response_hours: float
    resolution_hours: float
    business_hours_only: bool = True
    is_active: bool = True


# ==================== Email ====================

class EmailReplyRequest(BaseModel):
    ticket_id: str
    to_email: str
    subject: str
    body: str


class SimulatedEmail(BaseModel):
    from_email: str
    from_name: Optional[str] = None
    to_email: str = "support@emergent.sh"
    subject: str
    body: str


# ==================== Admin ====================

class CustomFieldCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    field_type: str = Field(..., description="text, number, select, date, boolean")
    entity_type: str = Field(..., description="ticket or user")
    options: Optional[List[str]] = None
    required: bool = False
    description: Optional[str] = None


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = None
    options: Optional[List[str]] = None
    required: Optional[bool] = None
    description: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = "json"
    include_notes: bool = True
    include_changelog: bool = True
    include_csat: bool = True
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status_filter: Optional[List[str]] = None


class AtlasImportRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ==================== Webhooks ====================

class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=10, max_length=500)
    events: List[str] = Field(..., min_items=1)
    secret: Optional[str] = Field(default=None, max_length=100)
    headers: Optional[Dict[str, str]] = Field(default={})
    is_active: bool = True

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @validator('events')
    def validate_events(cls, v):
        for event in v:
            if event not in WEBHOOK_EVENT_TYPES:
                raise ValueError(f'Invalid event type: {event}. Valid types: {", ".join(WEBHOOK_EVENT_TYPES)}')
        return v


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    url: Optional[str] = Field(default=None, max_length=500)
    events: Optional[List[str]] = None
    secret: Optional[str] = Field(default=None, max_length=100)
    headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None

    @validator('url')
    def validate_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @validator('events')
    def validate_events(cls, v):
        if v:
            for event in v:
                if event not in WEBHOOK_EVENT_TYPES:
                    raise ValueError(f'Invalid event type: {event}')
        return v


# ==================== Customers ====================

class CustomerCreate(BaseModel):
    name: str
    primary_email: EmailStr
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    priority_level: Optional[str] = "standard"
    net_payments: Optional[float] = 0.0
    assigned_agents: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    notes: Optional[str] = ""
    custom_fields: Optional[Dict[str, Any]] = {}


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    priority_level: Optional[str] = None
    net_payments: Optional[float] = None
    assigned_agents: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class LinkEmailRequest(BaseModel):
    email: EmailStr


class MergeCustomersRequest(BaseModel):
    source_customer_id: str
    target_customer_id: str


# ==================== CSAT ====================

class CSATRequest(BaseModel):
    ticket_id: str
    customer_email: str
    customer_name: Optional[str] = None


class CSATFeedbackRequest(BaseModel):
    feedback: Optional[str] = None
    was_resolved: Optional[bool] = None


class CSATRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ==================== Canned Responses ====================

class CannedResponseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    shortcode: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    content: str = Field(..., min_length=1, max_length=5000)
    scope: str = Field(default="global", pattern=r'^(global|personal)$')


class CannedResponseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    shortcode: Optional[str] = Field(None, min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    scope: Optional[str] = Field(None, pattern=r'^(global|personal)$')


# ==================== Search ====================

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit_per_category: int = Field(default=10, ge=1, le=50)
    type_filter: Optional[str] = None


# ==================== Feature Requests ====================

class FeatureRequestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    request_type: str = "feature"
    priority: Optional[str] = "medium"
    linked_ticket_id: Optional[str] = None


class FeatureRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    request_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


# ==================== Filters & Inboxes ====================

class FilterCondition(BaseModel):
    field: str
    op: str
    value: Any = None


class FilterGroup(BaseModel):
    logic: str = "and"
    conditions: List[FilterCondition] = []
    groups: List['FilterGroup'] = []


FilterGroup.model_rebuild()


class FilterRequest(BaseModel):
    filter_tree: FilterGroup
    page: int = 1
    limit: int = 50
    sort_by: str = "created_at"
    sort_order: str = "desc"


class InboxCreate(BaseModel):
    name: str
    filter_tree: FilterGroup
    color: Optional[str] = None
    icon: Optional[str] = None


class InboxUpdate(BaseModel):
    name: Optional[str] = None
    filter_tree: Optional[FilterGroup] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class InboxShare(BaseModel):
    user_ids: List[str]
