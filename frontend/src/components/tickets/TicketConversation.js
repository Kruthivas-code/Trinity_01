import React, { useState, useEffect } from 'react';
import {
  X, Trash2, Send, ChevronDown, Loader2, Star, MoreHorizontal,
  Mail, PenLine, Copy, Printer, BellOff, Merge, ExternalLink,
  Scissors, Bookmark, Download, UserPlus, MessageCircle, Activity,
  MessageSquare, ImagePlus, Paperclip, BookOpen, GitMerge, Filter, Unlink, Link, Users
} from 'lucide-react';
import RichTextEditor from '../common/RichTextEditor';
import MentionInput from '../common/MentionInput';
import ActivityTimeline from '../common/ActivityTimeline';
import EmailMessage, { getMergeColor, stripHtml, getInitials, getAvatarColor } from './EmailMessage';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const TicketConversation = ({
  ticket,
  // Header
  handleCopyTicketId, snoozed, isStarred, handleToggleStar,
  showMoreMenu, setShowMoreMenu,
  handleCopyLink, handleOpenInNewTab, handlePrint, handleToggleSnooze,
  handleAssignToMe,
  setShowMergeModal, setShowLinkModal, setShowSplitModal, setShowFeatureRequestModal,
  setSplitMessageIndex, setShowDeleteConfirm,
  handleCloseWithAnimation,
  // Tabs
  activeTab, setActiveTab,
  // Conversation ref
  conversationRef,
  // Activity/metadata
  activityFeed, loadingActivity,
  // Merge suggestions
  mergeSuggestions, dismissedMergeSuggestions, setDismissedMergeSuggestions,
  handleAcceptMergeSuggestion,
  // Merged tickets
  mergedTickets, showMergedPanel, setShowMergedPanel,
  handleUnmerge,
  // Message filtering
  messageSourceFilter, setMessageSourceFilter,
  // Conversation
  conversationThread, loadingNotes,
  handleSaveToKB,
  // Typing
  othersTyping,
  // Input
  inputMode, setInputMode,
  showCannedPicker, setShowCannedPicker,
  showKBPicker, setShowKBPicker,
  imageInputRef, uploadingImage,
  attachedImages,
  inputText, setInputText, setInputMentions,
  handleTypingChange, handleSubmitInput,
  submitting,
  handleCannedResponseSelect,
  handleImageUpload, removeAttachedImage,
  // CC
  ccEmails, setCcEmails,
  showCcField, setShowCcField,
}) => {
  const [emailStats, setEmailStats] = useState(null);
  useEffect(() => {
    if (!ticket?.ticket_id) return;
    fetch(`${BACKEND_URL}/api/tickets/${ticket.ticket_id}/email-stats`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setEmailStats(d); })
      .catch(() => {});
  }, [ticket?.ticket_id]);

  return (
    <div className="flex-1 bg-card border-l border-r border-border/40 flex flex-col min-w-0">
      {/* Header - Compact */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-border shrink-0 bg-card">
        <div className="flex items-center gap-2 min-w-0">
          <Mail size={15} className="text-foreground shrink-0" />
          <span className="text-sm font-medium truncate">{ticket.title}</span>
          <button
            onClick={handleCopyTicketId}
            className="text-[11px] text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded shrink-0 hover:bg-secondary/80 transition-colors cursor-pointer"
            title="Click to copy ticket ID"
            data-testid="copy-ticket-id"
          >
            {ticket.ticket_id || `#${ticket.id?.slice(-8)}`}
          </button>
          {snoozed && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">
              Snoozed
            </span>
          )}
        </div>
        <div className="flex items-center shrink-0">
          <button 
            onClick={handleToggleStar}
            className="h-6 w-6 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" 
            title={isStarred ? "Unstar ticket" : "Star ticket"}
            data-testid="drawer-star-button"
          >
            <Star 
              size={14} 
              className={isStarred ? "text-amber-400 fill-amber-400" : "text-muted-foreground"} 
            />
          </button>
          <div className="relative">
            <button 
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors" 
              title="More options"
              data-testid="drawer-more-button"
            >
              <MoreHorizontal size={14} className="text-muted-foreground" />
            </button>
            
            {/* More options dropdown */}
            {showMoreMenu && (
              <div className="absolute right-0 top-8 w-48 bg-popover border border-border rounded-lg shadow-xl z-50 py-1">
                <button
                  onClick={handleCopyLink}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-copy-link"
                >
                  <Copy size={14} className="text-muted-foreground" />
                  Copy link
                </button>
                <button
                  onClick={handleOpenInNewTab}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-open-new-tab"
                >
                  <ExternalLink size={14} className="text-muted-foreground" />
                  Open in new tab
                </button>
                <button
                  onClick={handlePrint}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-print"
                >
                  <Printer size={14} className="text-muted-foreground" />
                  Print ticket
                </button>
                <button
                  onClick={() => {
                    window.print();
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-export-pdf"
                >
                  <Download size={14} className="text-muted-foreground" />
                  Export as PDF
                </button>
                
                <div className="h-px bg-border my-1" />
                
                <button
                  onClick={handleToggleSnooze}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-snooze"
                >
                  <BellOff size={14} className={snoozed ? "text-amber-400" : "text-muted-foreground"} />
                  {snoozed ? 'Unsnooze ticket' : 'Snooze ticket'}
                </button>
                
                <button
                  onClick={handleAssignToMe}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-assign-me"
                >
                  <UserPlus size={14} className="text-muted-foreground" />
                  Assign to me
                </button>
                
                <div className="h-px bg-border my-1" />
                
                <button
                  onClick={() => {
                    setShowMergeModal(true);
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-merge"
                >
                  <Merge size={14} className="text-muted-foreground" />
                  Merge with ticket...
                </button>
                
                <button
                  onClick={() => {
                    setShowLinkModal(true);
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-link"
                >
                  <Link size={14} className="text-muted-foreground" />
                  Link to ticket...
                </button>
                
                <button
                  onClick={() => {
                    setSplitMessageIndex(null);
                    setShowSplitModal(true);
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-split"
                >
                  <Scissors size={14} className="text-muted-foreground" />
                  Split ticket...
                </button>
                
                <div className="h-px bg-border my-1" />
                
                <button
                  onClick={() => {
                    setShowFeatureRequestModal(true);
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/50 transition-colors text-left"
                  data-testid="more-feature-request"
                >
                  <Bookmark size={14} className="text-muted-foreground" />
                  Link to Feature Request...
                </button>
                
                <div className="h-px bg-border my-1" />
                
                <button
                  onClick={() => {
                    setShowDeleteConfirm(true);
                    setShowMoreMenu(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-500/10 transition-colors text-left text-red-400"
                  data-testid="more-delete"
                >
                  <Trash2 size={14} />
                  Delete ticket...
                </button>
              </div>
            )}
          </div>
          <button
            onClick={handleCloseWithAnimation}
            className="h-7 w-7 flex items-center justify-center rounded hover:bg-secondary/50 transition-colors ml-1"
            data-testid="drawer-close-button"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Tab Navigation - Compact */}
      <div className="flex items-center gap-0.5 px-4 py-1.5 border-b border-border bg-secondary/20">
        <button
          onClick={() => setActiveTab('conversation')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[13px] font-medium transition-colors ${
            activeTab === 'conversation'
              ? 'bg-foreground text-background'
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
          }`}
          data-testid="tab-conversation"
        >
          <MessageCircle size={13} />
          Conversation
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[13px] font-medium transition-colors ${
            activeTab === 'activity'
              ? 'bg-foreground text-background'
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
          }`}
          data-testid="tab-metadata"
        >
          <Activity size={13} />
          Metadata
        </button>
      </div>

      {/* Conversation Thread - Scrollable */}
      <div ref={conversationRef} className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        {/* Metadata Tab Content */}
        {activeTab === 'activity' && (
          <div className="space-y-3">
            {/* Email Metadata */}
            {ticket.source === 'email' && (ticket.email_sender || ticket.email_to) && (
              <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                <h4 className="text-xs font-medium text-muted-foreground mb-2">Email Details</h4>
                <div className="space-y-1.5 text-sm">
                  {ticket.email_sender && (
                    <div className="flex">
                      <span className="w-14 text-muted-foreground shrink-0">From:</span>
                      <span className="text-foreground truncate">{ticket.email_sender}</span>
                    </div>
                  )}
                  {ticket.email_to && (
                    <div className="flex">
                      <span className="w-14 text-muted-foreground shrink-0">To:</span>
                      <span className="text-foreground truncate">{ticket.email_to}</span>
                    </div>
                  )}
                  {ticket.email_cc && (
                    <div className="flex">
                      <span className="w-14 text-muted-foreground shrink-0">CC:</span>
                      <span className="text-foreground truncate">{ticket.email_cc}</span>
                    </div>
                  )}
                  {ticket.email_date && (
                    <div className="flex">
                      <span className="w-14 text-muted-foreground shrink-0">Date:</span>
                      <span className="text-foreground">{ticket.email_date}</span>
                    </div>
                  )}
                  {ticket.email_message_id && (
                    <div className="flex">
                      <span className="w-14 text-muted-foreground shrink-0">ID:</span>
                      <span className="text-foreground/60 text-xs font-mono truncate">{ticket.email_message_id}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Portal Ticket Metadata */}
            {ticket.source === 'portal' && (ticket.job_id || ticket.video_link || ticket.portal_category || ticket.tags?.length > 0) && (
              <div className="p-3 rounded-lg bg-secondary/20 border border-border/30" data-testid="portal-metadata">
                <h4 className="text-xs font-medium text-muted-foreground mb-2">Ticket Details</h4>
                <div className="space-y-1.5 text-sm">
                  {ticket.job_id && (
                    <div className="flex">
                      <span className="w-20 text-muted-foreground shrink-0">Job ID:</span>
                      <span className="text-foreground font-mono text-xs" data-testid="metadata-job-id">{ticket.job_id}</span>
                    </div>
                  )}
                  {ticket.video_link && (
                    <div className="flex">
                      <span className="w-20 text-muted-foreground shrink-0">Video:</span>
                      <a href={ticket.video_link} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline text-xs truncate" data-testid="metadata-video-link">{ticket.video_link}</a>
                    </div>
                  )}
                  {ticket.portal_category && (
                    <div className="flex">
                      <span className="w-20 text-muted-foreground shrink-0">Category:</span>
                      <span className="text-foreground">{ticket.portal_category}</span>
                    </div>
                  )}
                  {ticket.portal_subcategory && (
                    <div className="flex">
                      <span className="w-20 text-muted-foreground shrink-0">Subtopic:</span>
                      <span className="text-foreground">{ticket.portal_subcategory}</span>
                    </div>
                  )}
                  {ticket.tags?.length > 0 && (
                    <div className="flex">
                      <span className="w-20 text-muted-foreground shrink-0">Tags:</span>
                      <div className="flex flex-wrap gap-1">
                        {ticket.tags.map((t, i) => (
                          <span key={i} className="px-1.5 py-0.5 rounded bg-secondary/40 text-[10px] font-mono text-muted-foreground">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Activity Timeline */}
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-2">Activity Log</h4>
              <ActivityTimeline activities={activityFeed} loading={loadingActivity} />
            </div>
          </div>
        )}
        
        {/* Conversation Tab Content */}
        {activeTab === 'conversation' && (
          <>
        {/* Auto-merge Suggestions Banner */}
        {mergeSuggestions.length > 0 && mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).length > 0 && (
          <div className="mb-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30" data-testid="merge-suggestions-banner">
            <div className="flex items-start gap-2">
              <GitMerge size={16} className="text-amber-400 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-amber-400 mb-1">
                  {mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).length === 1
                    ? 'Possible duplicate detected'
                    : `${mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).length} possible duplicates detected`}
                </p>
                <p className="text-[11px] text-muted-foreground mb-2">
                  Same customer email within 2 hours
                </p>
                {mergeSuggestions.filter(s => !dismissedMergeSuggestions.includes(s.ticket_id)).map(suggestion => (
                  <div key={suggestion.ticket_id} className="flex items-center gap-2 py-1.5 border-t border-amber-500/20 first:border-t-0" data-testid={`merge-suggestion-${suggestion.ticket_id}`}>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs truncate">{suggestion.title}</p>
                      <p className="text-[10px] text-muted-foreground">{suggestion.ticket_id}</p>
                    </div>
                    <button
                      onClick={() => handleAcceptMergeSuggestion(suggestion.ticket_id)}
                      className="text-[10px] px-2 py-1 rounded bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
                      data-testid={`accept-merge-${suggestion.ticket_id}`}
                    >
                      Accept Merge
                    </button>
                    <button
                      onClick={() => setDismissedMergeSuggestions(prev => [...prev, suggestion.ticket_id])}
                      className="text-[10px] px-2 py-1 rounded text-muted-foreground hover:bg-secondary/50 transition-colors"
                      data-testid={`dismiss-merge-${suggestion.ticket_id}`}
                    >
                      Dismiss
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* Merged Tickets Info - Compact inline display */}
        {mergedTickets.length > 0 && (
          <div className="mb-3 p-2 rounded-lg bg-secondary/20 border border-border/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitMerge size={12} className="text-muted-foreground" />
                <span className="text-[11px] text-muted-foreground">
                  Contains {mergedTickets.length} merged {mergedTickets.length === 1 ? 'ticket' : 'tickets'}
                </span>
                <div className="flex items-center gap-1">
                  {mergedTickets.slice(0, 3).map((m, idx) => {
                    const color = getMergeColor(m.color_index || idx);
                    return (
                      <span key={m.ticket_id} className={`text-[10px] font-mono ${color.text}`}>
                        {m.ticket_id}
                      </span>
                    );
                  })}
                  {mergedTickets.length > 3 && (
                    <span className="text-[10px] text-muted-foreground">+{mergedTickets.length - 3}</span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setShowMergedPanel(!showMergedPanel)}
                className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                {showMergedPanel ? 'Hide' : 'Details'}
              </button>
            </div>
            
            {showMergedPanel && (
              <div className="mt-2 pt-2 border-t border-border/30 space-y-1.5">
                {mergedTickets.map((merged, idx) => {
                  const color = getMergeColor(merged.color_index || idx);
                  return (
                    <div key={merged.ticket_id} className="flex items-center justify-between py-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`text-[10px] font-mono ${color.text}`}>{merged.ticket_id}</span>
                        <span className="text-[11px] truncate">{merged.original_title}</span>
                      </div>
                      <button
                        onClick={() => handleUnmerge(merged.ticket_id)}
                        className="text-[10px] text-muted-foreground hover:text-foreground transition-colors shrink-0"
                        title="Unmerge"
                      >
                        <Unlink size={11} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        
        {/* Message Source Filter (when merged tickets exist) */}
        {mergedTickets.length > 0 && (
          <div className="mb-3 flex items-center gap-2">
            <Filter size={11} className="text-muted-foreground" />
            <select
              value={messageSourceFilter}
              onChange={(e) => setMessageSourceFilter(e.target.value)}
              className="text-xs bg-secondary/30 border border-border/40 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
              data-testid="message-source-filter"
            >
              <option value="all">All messages</option>
              <option value={ticket?.ticket_id}>{ticket?.ticket_id} (Original)</option>
              {mergedTickets.map((merged, idx) => (
                <option key={merged.ticket_id} value={merged.ticket_id}>
                  {merged.ticket_id} ({merged.original_title?.slice(0, 20)}...)
                </option>
              ))}
            </select>
          </div>
        )}
        
        {/* Current Conversation */}
        {loadingNotes && conversationThread.length === 1 ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={24} className="animate-spin text-muted-foreground" />
          </div>
        ) : (
          conversationThread
            .filter(msg => msg.type !== 'system')
            .filter(msg => messageSourceFilter === 'all' || 
              msg.original_ticket_id === messageSourceFilter || 
              (!msg.original_ticket_id && messageSourceFilter === ticket?.ticket_id))
            .map((msg, idx) => (
            <EmailMessage
              key={idx}
              type={msg.type}
              sender={msg.sender}
              senderEmail={msg.senderEmail}
              subject={msg.subject}
              content={msg.content}
              timestamp={msg.timestamp}
              isFirst={idx === 0}
              isAgentMessage={msg.isAgentMessage}
              originalTicketId={msg.original_ticket_id}
              mergeColorIndex={msg.merge_color_index}
              isMergeDivider={msg.type === 'merge_divider'}
              mergedTicketTitle={msg.merged_ticket_title}
              currentTicketId={ticket?.ticket_id}
              emailData={msg.emailData}
              source={msg.source}
              onSaveToKB={handleSaveToKB}
              ticketId={ticket?.ticket_id}
              emailStats={emailStats}
            />
          ))
        )}
          </>
        )}
      </div>

      {/* Typing Indicator Bubble */}
      {othersTyping.length > 0 && (
        <div className="shrink-0 px-3 py-2 border-t border-border/20 bg-secondary/20">
          <div className="flex items-center gap-2">
            <div className="flex -space-x-1">
              {othersTyping.slice(0, 3).map((typer, idx) => {
                const typerName = typer.name || typer.user_id || '?';
                const color = getAvatarColor(typerName);
                return (
                  <div 
                    key={typer.user_id || idx}
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold ring-2 ring-background"
                    style={{
                      backgroundColor: `${color}26`,
                      color: color,
                    }}
                    title={typerName}
                  >
                    {getInitials(typerName)}
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {othersTyping.length === 1 
                  ? (othersTyping[0].name || 'Someone')
                  : `${othersTyping.length} people`
                }
              </span>
              <span>{othersTyping.length === 1 ? 'is' : 'are'} typing</span>
              <span className="flex gap-0.5">
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Input Area - Fixed at bottom */}
      <div className="shrink-0 border-t border-border bg-background p-3">
        {/* Mode Toggle */}
        <div className="flex items-center gap-1 mb-2">
          <button
            onClick={() => setInputMode('reply')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
              inputMode === 'reply' 
                ? 'bg-foreground text-background' 
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
            }`}
            data-testid="mode-reply"
          >
            <Mail size={13} />
            <span>Reply</span>
            <span className="text-[10px] opacity-60 ml-0.5">R</span>
          </button>
          <button
            onClick={() => setInputMode('note')}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
              inputMode === 'note' 
                ? 'bg-amber-500 text-white' 
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
            }`}
            data-testid="mode-note"
          >
            <PenLine size={13} />
            <span>Note</span>
            <span className="text-[10px] opacity-60 ml-0.5">N</span>
          </button>
          
          <div className="w-px h-5 bg-border mx-1" />
          
          {/* CC Button - only in reply mode */}
          {inputMode === 'reply' && (
            <button
              onClick={() => setShowCcField(!showCcField)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                showCcField || (ccEmails && ccEmails.length > 0)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
              }`}
              title="Add CC recipients"
              data-testid="cc-toggle-btn"
            >
              <Users size={13} />
              <span>CC</span>
              {ccEmails && ccEmails.length > 0 && (
                <span className="text-[10px] bg-primary text-primary-foreground rounded-full w-4 h-4 flex items-center justify-center">{ccEmails.length}</span>
              )}
            </button>
          )}
          
          {/* Canned Responses Button */}
          <button
            onClick={() => setShowCannedPicker(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title="Insert canned response (⌘/)"
            data-testid="canned-responses-btn"
          >
            <MessageSquare size={13} />
            <span>Canned</span>
            <ChevronDown size={11} className="opacity-60" />
          </button>
          
          {/* Knowledge Base Button */}
          <button
            onClick={() => setShowKBPicker(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title="Insert KB article"
            data-testid="kb-picker-btn"
          >
            <BookOpen size={13} />
            <span>KB</span>
          </button>
          
          {/* Image Attachment Button */}
          <button
            onClick={() => imageInputRef.current?.click()}
            disabled={uploadingImage}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors disabled:opacity-50"
            title="Attach image"
            data-testid="attach-image-btn"
          >
            {uploadingImage ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <ImagePlus size={13} />
            )}
            <span>Image</span>
          </button>
          <input
            ref={imageInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageUpload}
            className="hidden"
            data-testid="image-input"
          />
          
          <div className="flex-1" />
          
          {/* Show attachment count if any */}
          {attachedImages.length > 0 && (
            <span className="flex items-center gap-1 text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">
              <Paperclip size={11} />
              {attachedImages.length}
            </span>
          )}
          
          <button
            onClick={handleSubmitInput}
            disabled={submitting || (!stripHtml(inputText).trim() && attachedImages.length === 0)}
            className={`h-8 px-5 flex items-center gap-1.5 rounded-md text-xs font-semibold transition-all duration-150 shrink-0 ${
              inputMode === 'note'
                ? 'bg-amber-500 text-white hover:bg-amber-600 active:scale-[0.97]'
                : 'bg-primary text-primary-foreground hover:brightness-110 active:scale-[0.97]'
            } disabled:opacity-30 disabled:cursor-not-allowed disabled:active:scale-100`}
            data-testid="submit-input"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            <span>Send</span>
          </button>
        </div>

        {/* Rich Text Editor for Reply / MentionInput for Notes */}
        {/* CC Field */}
        {showCcField && inputMode === 'reply' && (
          <div className="mb-2 flex items-center gap-2 bg-secondary/30 rounded px-2 py-1.5" data-testid="cc-field">
            <span className="text-xs text-muted-foreground font-medium shrink-0">CC:</span>
            <input
              type="text"
              placeholder="email1@example.com, email2@example.com"
              value={(ccEmails || []).join(', ')}
              onChange={(e) => {
                const raw = e.target.value;
                if (raw === '') {
                  setCcEmails([]);
                } else {
                  setCcEmails(raw.split(',').map(s => s.trim()));
                }
              }}
              className="flex-1 bg-transparent border-none outline-none text-xs text-foreground placeholder:text-muted-foreground/50"
              data-testid="cc-input"
            />
            <button
              onClick={() => { setCcEmails([]); setShowCcField(false); }}
              className="text-muted-foreground hover:text-foreground transition-colors"
              data-testid="cc-close-btn"
            >
              <X size={12} />
            </button>
          </div>
        )}
        {inputMode === 'note' ? (
          <MentionInput
            value={inputText}
            onChange={(text, mentions) => {
              setInputText(text);
              setInputMentions(mentions);
              handleTypingChange(text.length > 0);
            }}
            onSubmit={handleSubmitInput}
            placeholder="Add an internal note... Use @ to mention someone"
            disabled={submitting}
            rows={4}
          />
        ) : (
          <RichTextEditor
            value={inputText}
            onChange={(text) => {
              setInputText(text);
              handleTypingChange(stripHtml(text).trim().length > 0);
              
              const plainText = stripHtml(text);
              const lastSlashMatch = plainText.match(/(?:^|\s)\/([\\w-]*)$/);
              if (lastSlashMatch) {
                setShowCannedPicker(true);
              }
            }}
            placeholder="Type your reply..."
            mode={inputMode}
            onSubmit={handleSubmitInput}
            disabled={submitting}
          />
        )}
        
        {/* Attached Images Preview */}
        {attachedImages.length > 0 && (
          <div className="flex flex-wrap gap-2 px-3 py-2 bg-secondary/20 rounded-lg border border-border/30">
            {attachedImages.map((img) => (
              <div 
                key={img.id} 
                className="relative group"
                data-testid={`attached-image-${img.id}`}
              >
                <img 
                  src={img.url} 
                  alt={img.name}
                  className="h-16 w-auto rounded-md object-cover border border-border/40"
                />
                <button
                  onClick={() => removeAttachedImage(img.id)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg"
                  title="Remove image"
                  data-testid={`remove-image-${img.id}`}
                >
                  <X size={12} />
                </button>
                <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[9px] px-1 py-0.5 rounded-b-md truncate">
                  {img.name}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TicketConversation;
