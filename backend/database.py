"""
Database connection and collection references.
All MongoDB collections are defined here as the single source of truth.
"""
import os
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("server")

# MongoDB Connection
MONGO_URL = os.environ.get("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client[os.environ.get("DB_NAME")]

# Core collections
users_collection = db.users
tickets_collection = db.tickets
sessions_collection = db.user_sessions
api_keys_collection = db.api_keys
counters_collection = db.counters

# Email
email_replies_collection = db.email_replies

# Teams & Shifts
teams_collection = db.teams
messages_collection = db.messages
shifts_collection = db.shifts
user_shifts_collection = db.user_shifts

# Admin & Config
custom_fields_collection = db.custom_fields
admin_settings_collection = db.admin_settings
routing_rules_collection = db.routing_rules
sla_escalation_rules_collection = db.sla_escalation_rules

# Ticket Changelog
ticket_changelog_collection = db.ticket_changelog

# Feature Requests
feature_requests_collection = db.feature_requests

# Customers
customers_collection = db.customers

# Portal
portal_categories_collection = db.portal_categories
portal_customers_collection = db.portal_customers
portal_sessions_collection = db.portal_sessions

# CSAT
csat_responses_collection = db.csat_responses
csat_tokens_collection = db.csat_tokens

# Canned Responses
canned_responses_collection = db.canned_responses

# SLA Policies
sla_policies_collection = db.sla_policies

# Webhooks
webhooks_collection = db.webhooks
webhook_logs_collection = db.webhook_logs

# Custom Inboxes (Filters)
custom_inboxes_collection = db.custom_inboxes

# Notifications
notifications_collection = db.notifications

# Knowledge Base
knowledge_snippets_collection = db.knowledge_snippets

# ==================== Constants ====================

# Webhook event types
WEBHOOK_EVENT_TYPES = [
    "ticket.created",
    "ticket.updated",
    "ticket.assigned",
    "ticket.status_changed",
    "ticket.resolved",
    "ticket.closed",
    "ticket.deleted",
    "ticket.reply_added",
    "ticket.note_added",
    "customer.created",
    "customer.updated",
    "sla.breach",
    "sla.warning",
]

# B2C email domains
B2C_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.uk', 'yahoo.co.in',
    'hotmail.com', 'hotmail.co.uk', 'outlook.com', 'outlook.co.uk', 'live.com',
    'msn.com', 'aol.com', 'icloud.com', 'me.com', 'mac.com', 'protonmail.com',
    'proton.me', 'zoho.com', 'yandex.com', 'mail.com', 'gmx.com', 'gmx.net',
    'fastmail.com', 'tutanota.com', 'hey.com', 'pm.me', 'inbox.com',
    'rediffmail.com', 'qq.com', '163.com', '126.com', 'sina.com', 'sohu.com'
}

# System timezone
SYSTEM_TIMEZONE = "Asia/Kolkata"

# Input validation
MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 50000
MAX_TAGS = 50
MAX_TAG_LENGTH = 100
MAX_CUSTOM_FIELD_VALUE_LENGTH = 10000
VALID_STATUSES = ["todo", "in_progress", "waiting", "review", "resolved", "closed", "queued", "assigned"]
VALID_PRIORITIES = ["low", "medium", "high", "urgent"]
VALID_ESCALATION_LEVELS = ["L1", "L2", "L3"]
VALID_SOURCES = ["manual", "email", "api", "simulator", "atlas"]

# Role-based auth
VALID_ROLES = ["agent", "lead", "admin"]

# Emergent Auth
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
ALLOWED_DOMAIN = None

# Auto-close configuration
AUTO_CLOSE_HOURS = 24
