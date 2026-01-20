import React, { useState, useEffect } from 'react';
import { ArrowLeft, Mail, RefreshCw, Loader2, Ticket, CheckCircle, Clock, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const EmailsPage = ({ user }) => {
  const navigate = useNavigate();
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailDetail, setEmailDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [creatingTicket, setCreatingTicket] = useState(false);
  const [gmailConnected, setGmailConnected] = useState(false);

  useEffect(() => {
    checkGmailAndFetch();
  }, []);

  const checkGmailAndFetch = async () => {
    try {
      const statusRes = await fetch(`${BACKEND_URL}/api/gmail/status`, {
        credentials: 'include'
      });
      const status = await statusRes.json();
      setGmailConnected(status.connected);
      
      if (status.connected) {
        await fetchEmails();
      }
    } catch (error) {
      console.error('Error checking Gmail status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchEmails = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/emails?max_results=30`, {
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to fetch emails');
      
      const data = await response.json();
      setEmails(data.emails || []);
    } catch (error) {
      console.error('Error fetching emails:', error);
      toast.error('Failed to fetch emails');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchEmails();
    setRefreshing(false);
    toast.success('Emails refreshed');
  };

  const handleSelectEmail = async (email) => {
    setSelectedEmail(email);
    setLoadingDetail(true);
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/email/${email.id}`, {
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to fetch email details');
      
      const detail = await response.json();
      setEmailDetail(detail);
    } catch (error) {
      console.error('Error fetching email detail:', error);
      toast.error('Failed to load email details');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCreateTicket = async () => {
    if (!selectedEmail) return;
    
    setCreatingTicket(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/gmail/create-ticket/${selectedEmail.id}`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (!response.ok) throw new Error('Failed to create ticket');
      
      const ticket = await response.json();
      toast.success(`Ticket created: ${ticket.title}`);
      navigate('/dashboard');
    } catch (error) {
      console.error('Error creating ticket:', error);
      toast.error('Failed to create ticket');
    } finally {
      setCreatingTicket(false);
    }
  };

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const extractName = (fromStr) => {
    const match = fromStr.match(/^([^<]+)/);
    return match ? match[1].trim().replace(/"/g, '') : fromStr;
  };

  if (!user) return null;

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  if (!gmailConnected) {
    return (
      <div className="min-h-screen bg-background">
        <div className="gradient-overlay" />
        <div className="content-wrapper relative z-10">
          <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
            <div className="mx-auto max-w-[1400px] px-4 h-16 flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/10 transition-interactive"
              >
                <ArrowLeft size={20} />
              </button>
              <h1 className="text-xl font-semibold">Emails</h1>
            </div>
          </header>
          
          <div className="mx-auto max-w-[1400px] px-4 py-16 text-center">
            <Mail size={48} className="mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-medium mb-2">Gmail Not Connected</h2>
            <p className="text-muted-foreground mb-6">
              Connect your Gmail account to view and convert emails to tickets.
            </p>
            <button
              onClick={() => navigate('/settings')}
              className="px-6 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive"
            >
              Go to Settings
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="gradient-overlay" />
      <div className="content-wrapper relative z-10">
        {/* Header */}
        <header className="sticky top-0 z-40 glass border-b border-border/60 backdrop-saturate-150">
          <div className="mx-auto max-w-[1400px] px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="h-9 w-9 flex items-center justify-center rounded-lg hover:bg-white/10 transition-interactive"
                data-testid="back-button"
              >
                <ArrowLeft size={20} />
              </button>
              <h1 className="text-xl font-semibold">Emails</h1>
              <span className="text-sm text-muted-foreground">
                {emails.length} emails
              </span>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 hover:bg-secondary/70 transition-interactive disabled:opacity-50"
              data-testid="refresh-emails-button"
            >
              <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="mx-auto max-w-[1400px] px-4 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-120px)]">
            {/* Email List */}
            <div className="glass rounded-2xl border border-border/60 overflow-hidden flex flex-col">
              <div className="p-4 border-b border-border/40">
                <h2 className="font-medium">Inbox</h2>
              </div>
              
              <div className="flex-1 overflow-y-auto">
                {emails.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <Mail size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No emails found</p>
                  </div>
                ) : (
                  <div className="divide-y divide-border/40">
                    {emails.map((email) => (
                      <button
                        key={email.id}
                        onClick={() => handleSelectEmail(email)}
                        className={`w-full p-4 text-left hover:bg-white/5 transition-interactive ${
                          selectedEmail?.id === email.id ? 'bg-primary/10 border-l-2 border-l-primary' : ''
                        }`}
                        data-testid={`email-item-${email.id}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className="h-10 w-10 rounded-full bg-gradient-primary flex items-center justify-center text-white text-sm font-medium shrink-0">
                            {extractName(email.from).charAt(0).toUpperCase()}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <p className="font-medium truncate">
                                {extractName(email.from)}
                              </p>
                              <span className="text-xs text-muted-foreground whitespace-nowrap">
                                {formatDate(email.date)}
                              </span>
                            </div>
                            <p className="text-sm font-medium truncate mb-1">
                              {email.subject || '(No Subject)'}
                            </p>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {email.snippet}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Email Detail */}
            <div className="glass rounded-2xl border border-border/60 overflow-hidden flex flex-col">
              {selectedEmail ? (
                <>
                  <div className="p-4 border-b border-border/40 flex items-center justify-between">
                    <h2 className="font-medium truncate">Email Details</h2>
                    <button
                      onClick={handleCreateTicket}
                      disabled={creatingTicket}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-primary text-white hover:opacity-90 transition-interactive disabled:opacity-50"
                      data-testid="create-ticket-button"
                    >
                      {creatingTicket ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Ticket size={16} />
                      )}
                      <span>{creatingTicket ? 'Creating...' : 'Create Ticket'}</span>
                    </button>
                  </div>
                  
                  {loadingDetail ? (
                    <div className="flex-1 flex items-center justify-center">
                      <Loader2 size={24} className="animate-spin text-primary" />
                    </div>
                  ) : emailDetail ? (
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                      {/* Email Header */}
                      <div className="space-y-3">
                        <h3 className="text-lg font-medium">
                          {emailDetail.subject || '(No Subject)'}
                        </h3>
                        
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-gradient-primary flex items-center justify-center text-white text-sm font-medium">
                            {extractName(emailDetail.from).charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium">{extractName(emailDetail.from)}</p>
                            <p className="text-sm text-muted-foreground">
                              {emailDetail.from.match(/<([^>]+)>/)?.[1] || emailDetail.from}
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock size={14} />
                            {formatDate(emailDetail.date)}
                          </span>
                          {emailDetail.to && (
                            <span className="flex items-center gap-1">
                              <User size={14} />
                              To: {emailDetail.to}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Email Body */}
                      <div className="pt-4 border-t border-border/40">
                        <pre className="whitespace-pre-wrap text-sm font-sans leading-relaxed">
                          {emailDetail.body}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center text-muted-foreground">
                      <p>Failed to load email details</p>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Mail size={48} className="mx-auto mb-4 opacity-50" />
                    <p>Select an email to view details</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailsPage;
