import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Send, Loader2, Clock, User, Headphones } from 'lucide-react';
import { usePortalAuth } from './PortalAuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  todo: { label: 'Open', color: 'text-blue-500', bg: 'bg-blue-500/10 border-blue-500/20' },
  'in-progress': { label: 'In Progress', color: 'text-amber-500', bg: 'bg-amber-500/10 border-amber-500/20' },
  waiting: { label: 'Waiting', color: 'text-orange-500', bg: 'bg-orange-500/10 border-orange-500/20' },
  closed: { label: 'Closed', color: 'text-green-500', bg: 'bg-green-500/10 border-green-500/20' },
  closed: { label: 'Closed', color: 'text-muted-foreground', bg: 'bg-muted/50 border-muted-foreground/20' },
};

const PortalTicketDetail = () => {
  const { ticketId } = useParams();
  const { customer, token } = usePortalAuth();
  const [ticket, setTicket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const messagesEnd = useRef(null);

  useEffect(() => {
    if (!token) return;
    fetchTicket();
  }, [ticketId, token]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchTicket = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/tickets/${ticketId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTicket(data.ticket);
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!reply.trim()) return;
    setSending(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/tickets/${ticketId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ body: reply.trim() }),
      });
      if (res.ok) {
        setReply('');
        await fetchTicket();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSending(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr?.endsWith?.('Z') ? dateStr : dateStr + 'Z').toLocaleString('en-US', {
      timeZone: 'Asia/Kolkata',
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={20} className="animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground">Ticket not found</p>
        <Link to="/portal/my-tickets" className="text-sm text-foreground underline underline-offset-4 mt-2 inline-block">Back to tickets</Link>
      </div>
    );
  }

  const sc = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.todo;

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="portal-ticket-detail">
      {/* Back */}
      <Link to="/portal/my-tickets" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-6">
        <ArrowLeft size={12} />
        <span className="font-mono">my tickets</span>
      </Link>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[10px] font-mono text-muted-foreground/50">{ticket.ticket_id}</span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${sc.bg} ${sc.color}`}>
            {sc.label}
          </span>
          {ticket.portal_category && (
            <span className="text-[10px] font-mono text-muted-foreground/40">{ticket.portal_category}</span>
          )}
        </div>
        <h1 className="text-xl font-semibold text-foreground">{ticket.title}</h1>
        <p className="text-xs text-muted-foreground mt-1">
          Submitted {formatDate(ticket.created_at)}
        </p>
      </div>

      {/* Messages */}
      <div className="space-y-4 mb-8">
        {messages.map((msg, i) => {
          const isCustomer = msg.type === 'original' || msg.type === 'customer_reply';
          return (
            <div key={msg.message_id || i} className="flex gap-3" data-testid={`message-${i}`}>
              <div className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${isCustomer ? 'bg-foreground/10 text-foreground' : 'bg-blue-500/10 text-blue-500'}`}>
                {isCustomer ? <User size={13} /> : <Headphones size={13} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-xs font-medium text-foreground">
                    {isCustomer ? (msg.author_name || 'You') : (msg.author_name || 'Agent')}
                  </span>
                  <span className="text-[10px] text-muted-foreground/40">{formatDate(msg.created_at)}</span>
                </div>
                <div className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap break-words">
                  {msg.content}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEnd} />
      </div>

      {/* Reply box */}
      {!['closed'].includes(ticket.status) ? (
        <form onSubmit={handleReply} className="border border-border/40 rounded-lg bg-card overflow-hidden" data-testid="reply-form">
          <textarea
            value={reply}
            onChange={e => setReply(e.target.value)}
            placeholder="Write your reply..."
            rows={3}
            className="w-full px-4 py-3 text-sm text-foreground bg-transparent placeholder:text-muted-foreground/40 focus:outline-none resize-y"
            data-testid="reply-textarea"
          />
          <div className="flex items-center justify-end px-4 py-2.5 border-t border-border/20 bg-muted/10">
            <button
              type="submit"
              disabled={sending || !reply.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-[#00A1B2] text-white text-xs font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
              data-testid="reply-send-btn"
            >
              {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
              Send reply
            </button>
          </div>
        </form>
      ) : (
        <div className="p-4 rounded-lg border border-border/30 bg-muted/10 text-center">
          <p className="text-sm text-muted-foreground">This ticket is {ticket.status}. Contact us to reopen.</p>
        </div>
      )}
    </div>
  );
};

export default PortalTicketDetail;
