import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Clock, CheckCircle, AlertCircle, Loader2, Plus } from 'lucide-react';
import { usePortalAuth } from './PortalAuthContext';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  todo: { label: 'Open', color: 'text-blue-500', bg: 'bg-blue-500/10' },
  'in-progress': { label: 'In Progress', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  waiting: { label: 'Waiting', color: 'text-orange-500', bg: 'bg-orange-500/10' },
  closed: { label: 'Closed', color: 'text-green-500', bg: 'bg-green-500/10' },
  closed: { label: 'Closed', color: 'text-muted-foreground', bg: 'bg-muted/50' },
};

const PortalTickets = () => {
  const { customer, token } = usePortalAuth();
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    if (!customer || !token) { navigate('/portal/login?redirect=/portal/my-tickets'); return; }
    fetchTickets();
  }, [customer, token]);

  const fetchTickets = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/portal/tickets`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = filter === 'all' ? tickets : tickets.filter(t => t.status === filter);

  const timeAgo = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const diff = Date.now() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10" data-testid="portal-tickets-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold">My Tickets</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{tickets.length} ticket{tickets.length !== 1 ? 's' : ''}</p>
        </div>
        <Link
          to="/portal/submit"
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00A1B2] text-white text-sm font-medium hover:opacity-90 transition-opacity"
          data-testid="tickets-new-btn"
        >
          <Plus size={14} />
          New ticket
        </Link>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-1">
        {[
          { key: 'all', label: 'All' },
          { key: 'todo', label: 'Open' },
          { key: 'waiting', label: 'Waiting' },
          { key: 'closed', label: 'Closed' },
          { key: 'closed', label: 'Closed' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${filter === f.key ? 'bg-[#00A1B2] text-white' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}
            data-testid={`filter-${f.key}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={20} className="animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 border border-border/30 rounded-lg bg-card/50">
          <p className="text-muted-foreground text-sm mb-3">
            {filter === 'all' ? "You haven't submitted any tickets yet" : `No ${filter} tickets`}
          </p>
          <Link to="/portal/submit" className="text-sm text-foreground underline underline-offset-4">
            Submit your first ticket
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(ticket => {
            const sc = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.todo;
            return (
              <Link
                key={ticket.ticket_id}
                to={`/portal/my-tickets/${ticket.ticket_id}`}
                className="block p-4 rounded-lg border border-border/40 bg-card hover:border-foreground/15 hover:shadow-sm transition-all group"
                data-testid={`ticket-row-${ticket.ticket_id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono text-muted-foreground/50">{ticket.ticket_id}</span>
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${sc.bg} ${sc.color}`}>
                        {sc.label}
                      </span>
                    </div>
                    <h3 className="text-sm font-medium text-foreground truncate group-hover:translate-x-0.5 transition-transform">
                      {ticket.title}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-muted-foreground/40">{timeAgo(ticket.updated_at)}</span>
                    <ArrowRight size={12} className="text-muted-foreground/30 group-hover:text-foreground/50 transition-colors" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PortalTickets;
