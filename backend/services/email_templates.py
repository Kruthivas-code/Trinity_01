"""
HTML and plain text email templates for Trinity.
Brand color: #00A1B2
"""

BRAND_COLOR = "#00A1B2"

def _base_html(content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:32px 16px;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;background:#ffffff;border-radius:12px;overflow:hidden;">
<tr><td style="padding:32px 32px 24px;">
<img src="https://app.emergent.sh/images/emergent-logo-dark.png" alt="Emergent" height="24" style="display:block;margin-bottom:24px;">
{content}
</td></tr>
<tr><td style="padding:16px 32px 24px;border-top:1px solid #e4e4e7;">
<p style="margin:0;font-size:12px;color:#a1a1aa;line-height:1.5;">
This email was sent by Emergent Support.<br>
If you did not expect this email, you can safely ignore it.
</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def ticket_confirmation_html(ticket_id: str, customer_name: str, subject: str) -> str:
    return _base_html(f"""
<h2 style="margin:0 0 8px;font-size:20px;font-weight:600;color:#18181b;">We received your request</h2>
<p style="margin:0 0 24px;font-size:14px;color:#71717a;line-height:1.6;">
Hi {customer_name}, thanks for reaching out. We've created a ticket for your request and our team will get back to you shortly.
</p>
<table cellpadding="0" cellspacing="0" style="width:100%;background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:24px;">
<tr><td>
<p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.5px;">Ticket</p>
<p style="margin:0 0 12px;font-size:14px;color:#18181b;font-weight:500;">{ticket_id}</p>
<p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.5px;">Subject</p>
<p style="margin:0;font-size:14px;color:#18181b;font-weight:500;">{subject}</p>
</td></tr>
</table>
<p style="margin:0;font-size:14px;color:#71717a;line-height:1.6;">
You can reply directly to this email to add more details to your ticket.
</p>
""")


def ticket_confirmation_text(ticket_id: str, customer_name: str, subject: str) -> str:
    return f"""Hi {customer_name},

We received your request and created ticket {ticket_id}.

Subject: {subject}

Our team will get back to you shortly. You can reply directly to this email to add more details.

— Emergent Support"""


def agent_reply_html(ticket_id: str, customer_name: str, subject: str, reply_content: str, agent_name: str) -> str:
    # Convert newlines to <br> for HTML display
    reply_html = reply_content.replace("\n", "<br>")
    return _base_html(f"""
<p style="margin:0 0 16px;font-size:14px;color:#71717a;">
Hi {customer_name}, {agent_name} from our team replied to your ticket:
</p>
<div style="background:#f9fafb;border-left:3px solid {BRAND_COLOR};border-radius:0 8px 8px 0;padding:16px;margin-bottom:24px;">
<p style="margin:0;font-size:14px;color:#18181b;line-height:1.6;">{reply_html}</p>
</div>
<p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;">Ticket: {ticket_id}</p>
<p style="margin:0;font-size:14px;color:#71717a;line-height:1.6;">
Reply directly to this email to continue the conversation.
</p>
""")


def agent_reply_text(ticket_id: str, customer_name: str, subject: str, reply_content: str, agent_name: str) -> str:
    return f"""Hi {customer_name},

{agent_name} from our team replied to your ticket ({ticket_id}):

{reply_content}

Reply directly to this email to continue the conversation.

— Emergent Support"""


def status_update_html(ticket_id: str, customer_name: str, subject: str, new_status: str) -> str:
    status_label = new_status.replace("_", " ").title()
    status_color = {
        "resolved": "#22c55e",
        "closed": "#22c55e",
        "closed": "#a1a1aa",
        "in_progress": "#f59e0b",
        "waiting": "#f97316",
        "todo": "#3b82f6",
    }.get(new_status, BRAND_COLOR)

    return _base_html(f"""
<p style="margin:0 0 16px;font-size:14px;color:#71717a;">
Hi {customer_name}, there's an update on your ticket:
</p>
<table cellpadding="0" cellspacing="0" style="width:100%;background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:24px;">
<tr><td>
<p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.5px;">Ticket</p>
<p style="margin:0 0 12px;font-size:14px;color:#18181b;font-weight:500;">{ticket_id}</p>
<p style="margin:0 0 4px;font-size:12px;color:#a1a1aa;text-transform:uppercase;letter-spacing:0.5px;">Status</p>
<p style="margin:0;font-size:14px;font-weight:600;color:{status_color};">{status_label}</p>
</td></tr>
</table>
<p style="margin:0;font-size:14px;color:#71717a;line-height:1.6;">
{"If you have any further questions, reply directly to this email." if new_status not in ("closed",) else "This ticket has been closed. If you need further help, please submit a new ticket."}
</p>
""")


def status_update_text(ticket_id: str, customer_name: str, subject: str, new_status: str) -> str:
    status_label = new_status.replace("_", " ").title()
    return f"""Hi {customer_name},

Your ticket {ticket_id} has been updated.

Status: {status_label}

{"Reply to this email if you have further questions." if new_status != "closed" else "This ticket has been closed. If you need further help, please submit a new ticket."}

— Emergent Support"""
