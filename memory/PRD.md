# Trinity — Product Requirements Document

## Overview
Trinity is a comprehensive customer help suite consisting of three main parts:
1. **Knowledge Base** (`/`) — Public-facing documentation site
2. **Help Portal** (`/portal`) — Customer-facing ticket triage funnel
3. **Agent Dashboard** (`/dashboard`) — Internal tool for engineers to manage tickets and KB

## Tech Stack
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: Gemini (via emergentintegrations) for ticket summarization
- **Email**: Amazon SES SMTP (sending) + Gmail IMAP (receiving)
- **Brand Color**: `#00A1B2`

## Credentials
- Admin: `test@example.com` / `test`
- Portal: Self-registration (or kruthivas@emergent.sh / Password123)

## Email System Architecture

### Outbound (SES SMTP)
- `smtplib` → `email-smtp.us-east-1.amazonaws.com:587`
- From: `Emergent Support <support@emergent.sh>`
- Threading: `Message-ID`, `In-Reply-To`, `References` headers
- Triggers: ticket confirmation, agent reply (type='reply'), status change (resolved/closed/in_progress)
- Rate limited: 10 emails/sec (SES allows 14)
- Failed emails → retry queue with exponential backoff (max 5 retries, max 1hr backoff)
- All Message-IDs stored in `email_threads` collection

### Inbound (IMAP Polling)
- `imaplib` → `imap.gmail.com:993` (hey@emergent.sh, alias: support@emergent.sh)
- Polls every 30s for UNSEEN emails
- Ticket matching: In-Reply-To → References → sender + recent ticket fallback
- Strips quoted text, sanitizes body (XSS prevention, null bytes, HTML stripping)
- Deduplication via Message-ID tracking
- Auto-reconnect with exponential backoff
- Processes retry queue every 5 cycles (~2.5 min)

### Dashboard Integration
- Messages show "via email" (teal badge) or "via portal" (gray badge)
- Source field on messages: `source: "email"` for IMAP, `source: "portal"` for portal

### Email Templates
- Branded HTML with `#00A1B2` accent, responsive design
- Plain text fallback included
- Templates: ticket confirmation, agent reply, status update

## Completed Work

### Feb 2026 — Email Phase 2
- Production-grade email service with thread-safe rate limiting
- Retry queue for failed emails with exponential backoff
- IMAP connection resilience (graceful error recovery, auto-reconnect)
- Input sanitization on inbound email body (XSS prevention, HTML stripping)
- Structured logging ([SEND], [INBOUND], [POLL], [RETRY] prefixes)
- "via email" / "via portal" source badges on ticket messages
- 13 unit tests (all passing): SES region detection, send/fail flows, rate limiting, sanitization, threading, dedup, retry
- Testing agent: 26/26 tests pass, zero critical issues

### Feb 2026 — Email Phase 1
- SES SMTP sending integration
- IMAP inbox polling
- Email threading (Message-ID, In-Reply-To, References)
- MongoDB email_threads collection

### Feb 2026 — UI/UX Updates
- KB sidebar redesign (collapsible groups, no icons, white bg)
- Dark mode neutral grey text (#999999, #787878) across all components
- Portal UI overhaul (consistent header, brand colors, 960px width, 3-col grid, search)
- Portal dark mode page-load fix
- Portal auth body-stream bug fix
- Docs header: "Need Help" as primary CTA

## Pending / Backlog

### P0
- Align Help Portal categories with user's list (4 discrepancies pending user input)

### P1
- Bounce/complaint handling via SES notifications
- Email delivery status tracking (delivered/bounced)

### P2
- Real-time notifications for agents
- Refactor KBEditor.js into smaller components
- Refactor portal categories to backend-managed
