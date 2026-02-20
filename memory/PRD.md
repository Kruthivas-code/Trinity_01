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
- **Email**: Amazon SES (SMTP) for sending, Gmail IMAP for receiving
- **Brand Color**: `#00A1B2`

## Credentials
- Admin: `test@example.com` / `test`
- Portal: Self-registration

## Architecture

### Knowledge Base
- Light/dark theme with `dark:` Tailwind variants
- Categories in collapsible left sidebar (tabs → groups → pages)
- Full-screen search modal with highlighted results
- Brand color `#00A1B2` throughout
- Dark mode text: `#999999` (muted), `#787878` (secondary), white (headings)
- Sidebar: white bg in light mode, `#0a0a0a` in dark mode

### Help Portal
- Header consistent with docs (Logo, "Docs" CTA in brand color, theme toggle)
- Content max-width: 960px
- Cards: white bg, `border-gray-200`, `rounded-2xl`, `hover:border-[#00A1B2]`
- 3-column category grid with search filtering
- Brand color on primary actions, grey on secondary card CTAs

### Email System (Phase 1 — Implemented Feb 2026)
**Outbound (SES SMTP):**
- `smtplib` → `email-smtp.us-east-1.amazonaws.com:587`
- From: `support@emergent.sh`
- Threading headers: `Message-ID`, `In-Reply-To`, `References`
- Triggers: ticket confirmation, agent reply, status change (resolved/closed/in_progress)
- All Message-IDs stored in `email_threads` collection

**Inbound (IMAP Polling):**
- `imaplib` → `imap.gmail.com:993` (hey@emergent.sh mailbox, support@emergent.sh alias)
- Polls every 30s for UNSEEN emails
- Ticket matching: In-Reply-To → References → sender + recent ticket fallback
- Strips quoted text, adds reply to ticket thread
- Deduplication via Message-ID tracking
- Auto-reconnect with exponential backoff

**Email Templates:**
- Branded HTML with `#00A1B2` accent
- Responsive, clean design
- Plain text fallback included

## Completed Work

### Feb 2026 — This Session
- KB sidebar redesign (tabs as plain text, groups as collapsible dropdowns, no icons)
- Sidebar bg changed to white in light mode
- Dark mode text colors updated to neutral greys (#999999, #787878)
- All slate colors replaced across DocContent, Accordion, Cards, Steps, Tabs
- Portal UI overhaul: consistent header, brand colors, 960px max-width, 3-col grid
- Portal search functionality for browsing topics
- Portal page-load dark mode fix (dark class sync in PortalLayout)
- Docs header: removed "Try Emergent", "Need Help" is primary CTA
- Portal auth fix: res.text() + JSON.parse() to prevent body stream errors
- **Email system Phase 1**: SES SMTP sending + IMAP receiving fully implemented

### Previous Sessions
- KB full redesign (light/dark theme, brand color, search modal, TOC, cards)
- Help Portal ticket triage funnel
- Agent Dashboard with AI summarization
- CORS fix, webpack fix, escalation label simplification

## Pending / Backlog

### P0
- Align Help Portal categories with user's list (4 discrepancies pending user input)

### P1
- Email Phase 2: Dashboard UI for email status (sent/delivered/bounced)
- Email thread visualization in ticket view
- Failed email retry mechanism

### P2
- Real-time notifications for agents
- Refactor KBEditor.js into smaller components
- Refactor portal categories to backend-managed
- Bounce/complaint handling via SES notifications
