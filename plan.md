# Email Handling Overhaul - Production-Grade Implementation

## Status: IN PROGRESS

## Testing Email: rohit@emergent.sh

---

## Phase 1: Email Threading Fix (Status: COMPLETED ✅)
**Goal:** Ensure replies are correctly threaded in recipients' email clients.

### Completed Work:
- ✅ Created `email_utils.py` with RFC 2822 header parsing (`Message-ID`, `In-Reply-To`, `References`)
- ✅ `build_threading_headers()` function correctly builds reply headers
- ✅ `generate_message_id()` creates valid RFC 2822 Message-IDs
- ✅ Backend `reply_to_ticket()` uses proper threading headers
- ✅ Auto sync stores `email_rfc_message_id` and `email_references` from incoming emails

---

## Phase 2: Email Storage Enhancement (Status: COMPLETED ✅)
**Goal:** Store different versions of the email body for different use cases.

### Completed Work:
- ✅ `parse_email_content()` extracts `html`, `text`, and `preview` from email payload
- ✅ Auto sync stores `email_html`, `email_text`, `email_preview` fields in ticket documents
- ✅ Content is capped appropriately (HTML: 100KB, text: 50KB, preview: 150 chars)

---

## Phase 3: Email Rendering Fix (Status: IN PROGRESS 🔄)
**Goal:** Display emails correctly on the frontend.

### Completed Work:
- ✅ Created `EmailViewer.js` component with:
  - Safe HTML rendering via DOMPurify in sandboxed iframe
  - Toggle between HTML/plain text views
  - Image loading controls
  - Expand/collapse functionality
- ✅ `TicketsListView.js` uses `getPreviewText()` to show clean text previews
- ✅ `EmailViewer.js` imported in `TicketDrawer.js`

### Remaining Work:
- [ ] Integrate `EmailViewer` into the conversation thread for email tickets
- [ ] Pass `email_html` and `email_text` data to the EmailViewer component
- [ ] Test complete email view with rich HTML content

---

## Phase 4: Testing & Verification (Status: NOT STARTED)
- [ ] Test email sync with various HTML email types
- [ ] Test email reply threading (send to rohit@emergent.sh)
- [ ] Verify replies appear in same thread in recipient's inbox
- [ ] Screenshot verification of email rendering

---

## Technical Notes

### Backend Fields for Email Tickets:
```python
{
  "email_message_id": "...",          # Gmail's internal ID
  "email_thread_id": "...",           # Gmail's thread ID
  "email_rfc_message_id": "...",      # RFC 2822 Message-ID for threading
  "email_references": "...",          # References header chain
  "email_in_reply_to": "...",         # In-Reply-To header
  "email_sender": "...",              # From header
  "email_html": "...",                # Full HTML body
  "email_text": "...",                # Plain text body  
  "email_preview": "...",             # 150-char preview
}
```

### Frontend Components:
- `EmailViewer.js`: Safe HTML rendering in sandboxed iframe
- `TicketDrawer.js`: Main ticket view - needs to use EmailViewer
- `TicketsListView.js`: Uses `email_preview` for clean list display
