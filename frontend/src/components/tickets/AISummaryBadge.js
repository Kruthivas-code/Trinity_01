import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, ChevronDown, ChevronRight, RefreshCw, Loader2, History } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AISummaryBadge = ({ ticketId }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSummary = useCallback(async (force = false) => {
    if (!ticketId) return;
    try {
      if (force) setRefreshing(true);
      else setLoading(true);
      const url = `${BACKEND_URL}/api/tickets/${ticketId}/summary${force ? '?force=true' : ''}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
        if (data.eligible && !expanded && !force) setExpanded(true);
      }
    } catch (err) {
      console.error('Failed to fetch summary:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [ticketId]);

  useEffect(() => {
    setSummary(null);
    setExpanded(false);
    setLoading(true);
    fetchSummary();
  }, [ticketId, fetchSummary]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-2 text-muted-foreground">
        <Loader2 size={12} className="animate-spin" />
        <span className="text-[11px]">Checking summary...</span>
      </div>
    );
  }

  if (!summary || !summary.eligible) return null;

  return (
    <div data-testid="ai-summary-section">
      <div className="w-full flex items-center justify-between py-1.5 group">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2"
          data-testid="ai-summary-toggle"
        >
          <div className="h-5 w-5 rounded flex items-center justify-center bg-violet-500/20">
            <Sparkles size={11} className="text-violet-400" />
          </div>
          <span className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider">AI Summary</span>
        </button>
        <div className="flex items-center gap-1">
          {summary.cached && (
            <button
              onClick={() => fetchSummary(true)}
              disabled={refreshing}
              className="p-0.5 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors"
              title="Refresh summary"
              data-testid="ai-summary-refresh"
            >
              {refreshing ? (
                <Loader2 size={11} className="animate-spin" />
              ) : (
                <RefreshCw size={11} />
              )}
            </button>
          )}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-0.5 text-muted-foreground"
          >
            {expanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-1 space-y-2.5 animate-in fade-in duration-200" data-testid="ai-summary-content">
          {/* Conversation Summary */}
          {summary.conversation_summary && (
            <div className="rounded-lg bg-violet-500/5 border border-violet-500/15 p-2.5">
              <div className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider mb-1.5">
                Conversation
              </div>
              <p className="text-[11px] leading-relaxed text-foreground/80" data-testid="conversation-summary-text">
                {summary.conversation_summary}
              </p>
            </div>
          )}

          {/* Past Issues */}
          {summary.past_issues_summary && summary.past_ticket_count > 0 && (
            <div className="rounded-lg bg-amber-500/5 border border-amber-500/15 p-2.5">
              <div className="flex items-center gap-1.5 mb-1.5">
                <History size={10} className="text-amber-400" />
                <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                  Past Issues ({summary.past_ticket_count})
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-foreground/80" data-testid="past-issues-summary-text">
                {summary.past_issues_summary}
              </p>
            </div>
          )}

          {/* Metadata */}
          {summary.generated_at && (
            <div className="text-[9px] text-muted-foreground/50 text-right">
              {summary.cached ? 'Cached' : 'Generated'} {new Date(summary.generated_at).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AISummaryBadge;
