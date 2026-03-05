# Trinity — Product Requirements Document

## Overview
Trinity is a comprehensive customer help suite with three public surfaces and one internal tool:

1. **Knowledge Base** (`/`, `/docs/:slug`) — Public documentation site
2. **Help Portal** (`/portal`) — Customer-facing ticket submission and tracking
3. **Agent Dashboard** (`/dashboard`, `/all-tickets`) — Internal agent tool
4. **CSAT** (`/csat/:token`) — Customer satisfaction surveys

## Tech Stack
- **Frontend**: React 18 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python) + Socket.IO (real-time)
- **Database**: MongoDB (pymongo)
- **AI**: Gemini via `emergentintegrations` for ticket summarization
- **Email Outbound**: Amazon SES SMTP (with CC support)
- **Email Inbound**: Gmail IMAP polling
- **Auth**: Emergent Google OAuth (dashboard), JWT sessions (portal)

---

## Completed Work

### Email CC & Outbound Tickets (Mar 5, 2026)
- **CC on replies**: CC button in reply composer, CC addresses sent in email headers, stored on records
- **Agent-initiated outbound tickets**: Create Ticket modal with customer email, send email toggle, CC field
- **Enhanced bounce tooltip**: Detailed hover showing bounced email, reason, timestamp, CC info
- Backend: `send_email()` CC support, `email-stats` returns `bounce_details` and `outbound_emails`

### Atlas Full Metadata Import (Mar 5, 2026)
- **Backfill COMPLETE**: 67,135 conversations, 344K+ messages, 0 errors
- **Agent import**: 163 Atlas agents imported, merge-safe by email
- **Full metadata**: CSAT scores, attachments (URL refs), sub-channels, actor tracking, environment info
- **Customer enrichment**: Atlas custom fields, phone, company ID on customer records
- **Enrichment pass**: Running (3,700/~45K old tickets patched)

### Previous Work
- KB Editor (Columns, Accordion, Steps, Icon Picker)
- Backend-driven Portal Categories
- Full Gmail Thread Capture with correct timestamps
- Email System (SES outbound, IMAP inbound, threading)

---

## In Progress
- **Enrichment pass**: Patching ~45K pre-update tickets with new metadata (auto-resumes)

## Pending / Backlog

### P0: Atlas Real-Time Sync (Shadow Mode)
- Enhance `atlas_sync.py` for full conversation sync
- Background worker polling every 60s
- Admin controls and monitoring

### P1: Data Validation (Post-Enrichment)
- Count verification, message integrity, timestamp sanity

### P2: Future
- Blob storage for attachment migration
- Real-time notifications for agents
- Auto-closing stale tickets
- Tag definitions & SLA rule import
- Email analytics dashboard
