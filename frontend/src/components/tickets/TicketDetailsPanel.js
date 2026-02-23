import React, { useState, useEffect } from 'react';
import {
  X, ChevronDown, ChevronRight, Loader2, Star, AlertCircle,
  Sparkles, Link2, Settings, Users, Clock, ArrowUpCircle, UserCheck,
  Copy, Bookmark, Scissors, Tag, MessageSquareHeart, Mail, Send, UserPlus,
  CheckCircle, XCircle, AlertTriangle as TriangleAlert
} from 'lucide-react';
import AISummaryBadge from './AISummaryBadge';
import { STATUSES, PRIORITIES, ESCALATION_LEVELS } from '../../hooks/useTicketDrawer';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const EmailDeliveryStatus = ({ ticketId }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!ticketId) return;
    fetch(`${BACKEND_URL}/api/tickets/${ticketId}/email-stats`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setStats(d); })
      .catch(() => {});
  }, [ticketId]);

  if (!stats || (stats.outbound === 0 && stats.inbound === 0)) return null;

  return (
    <div className="pt-1.5 mt-1.5 border-t border-border/20" data-testid="email-delivery-status">
      <div className="flex items-center gap-1.5 mb-1">
        <Mail size={10} className="text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground">Email</span>
      </div>
      <div className="flex items-center gap-3">
        {stats.outbound > 0 && (
          <div className="flex items-center gap-1" title={`${stats.outbound} email(s) sent`}>
            <CheckCircle size={10} className="text-emerald-500" />
            <span className="text-[10px] text-emerald-600">{stats.outbound} sent</span>
          </div>
        )}
        {stats.bounced > 0 && (
          <div className="flex items-center gap-1" title={`${stats.bounced} email(s) bounced`}>
            <XCircle size={10} className="text-red-500" />
            <span className="text-[10px] text-red-500">{stats.bounced} bounced</span>
          </div>
        )}
        {stats.failed > 0 && (
          <div className="flex items-center gap-1" title={`${stats.failed} email(s) failed`}>
            <TriangleAlert size={10} className="text-amber-500" />
            <span className="text-[10px] text-amber-500">{stats.failed} failed</span>
          </div>
        )}
        {stats.inbound > 0 && (
          <div className="flex items-center gap-1" title={`${stats.inbound} email reply(s) received`}>
            <Mail size={10} className="text-teal-500" />
            <span className="text-[10px] text-teal-600">{stats.inbound} received</span>
          </div>
        )}
      </div>
    </div>
  );
};

const TicketDetailsPanel = ({
  ticket, users, currentUser,
  formData, setFormData,
  showDeleteConfirm, setShowDeleteConfirm,
  handleDelete,
  escalating, handleEscalate,
  assignmentOptions, showAssignDropdown, setShowAssignDropdown,
  handleAssignToMe, handleAssign, handleAssignToTeam,
  statusConfig, priorityConfig, assignee,
  sectionsExpanded, toggleSection,
  linkedFeatureRequests, handleUnlinkFeatureRequest,
  setShowFeatureRequestModal,
  linkedTickets, handleUnlinkTicket,
  setShowLinkModal,
  handleCopyLink,
  ticketTags, tagInput, setTagInput,
  showTagDropdown, setShowTagDropdown,
  filteredTags, loadingTags, availableTags,
  handleAddTag, handleRemoveTag,
  csatData, sendingCsat, handleSendCsat,
  customFields, customFieldValues, setCustomFieldValues,
}) => {
  return (
    <div className="w-72 bg-card border-l border-border flex flex-col shrink-0">
      {/* Tabs */}
      <div className="h-12 px-4 flex items-center gap-4 border-b border-border shrink-0">
        <button className="text-sm font-semibold text-foreground relative pb-0.5">
          Details
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground rounded-full" />
        </button>
      </div>

      {/* Details Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Escalation Level */}
        <div>
          <label className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
            <ArrowUpCircle size={11} />
            Escalation Level
          </label>
          <div className="flex gap-1">
            {ESCALATION_LEVELS.map(level => (
              <button
                key={level.value}
                onClick={() => handleEscalate(level.value)}
                disabled={escalating || formData.escalation_level === level.value}
                className={`flex-1 h-8 px-2 text-[11px] font-semibold rounded-md transition-all duration-150 ${
                  formData.escalation_level === level.value
                    ? `${level.color} text-white shadow-sm`
                    : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent hover:border-border'
                } ${escalating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                data-testid={`escalation-${level.value}`}
              >
                {escalating && formData.escalation_level !== level.value ? (
                  <Loader2 size={12} className="animate-spin mx-auto" />
                ) : (
                  level.value
                )}
              </button>
            ))}
          </div>
          {assignmentOptions?.current_team && (
            <div className="flex items-center gap-1.5 mt-1.5 text-[10px] text-muted-foreground">
              <Users size={10} />
              <span>Team: {assignmentOptions.current_team.name}</span>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="h-px bg-border/30" />

        {/* AI Summary */}
        <AISummaryBadge ticketId={ticket.ticket_id || ticket.id} />

        {/* Divider */}
        <div className="h-px bg-border/30" />

        {/* Assignee */}
        <div className="relative">
          <label className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
            <UserCheck size={11} />
            Assignee
          </label>
          
          <button
            onClick={() => setShowAssignDropdown(!showAssignDropdown)}
            className="w-full h-8 px-2 text-sm rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-foreground/20 text-left flex items-center justify-between transition-shadow"
            data-testid="drawer-assignee-dropdown"
          >
            <span className={formData.assignee_id ? '' : 'text-muted-foreground'}>
              {assignee ? assignee.name : 'Unassigned'}
            </span>
            <ChevronDown size={14} className="text-muted-foreground" />
          </button>

          {/* Dropdown menu */}
          {showAssignDropdown && (
            <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-64 overflow-y-auto">
              <button
                onClick={() => {
                  setFormData({ ...formData, assignee_id: null });
                  setShowAssignDropdown(false);
                }}
                className="w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 text-muted-foreground"
              >
                Unassigned
              </button>
              
              {currentUser && (
                <button
                  onClick={handleAssignToMe}
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-primary/10 flex items-center gap-2 border-b border-border/30 ${
                    formData.assignee_id === (currentUser.user_id || currentUser.id) ? 'bg-primary/10 text-primary' : 'text-primary'
                  }`}
                  data-testid="assign-to-me-button"
                >
                  <UserPlus size={14} />
                  <span>Assign to me</span>
                  {formData.assignee_id === (currentUser.user_id || currentUser.id) && (
                    <span className="ml-auto text-[10px]">&check;</span>
                  )}
                </button>
              )}
              
              {/* Team Members Section */}
              {assignmentOptions?.team_members?.length > 0 && (
                <>
                  <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30 flex items-center gap-1.5">
                    <Users size={10} />
                    Team Members
                    {assignmentOptions.current_team && (
                      <span className="ml-auto opacity-60">({assignmentOptions.current_team.name})</span>
                    )}
                  </div>
                  {assignmentOptions.team_members
                    .filter(m => m.user_id !== (currentUser?.user_id || currentUser?.id))
                    .map(member => (
                    <button
                      key={member.user_id}
                      onClick={() => handleAssign(member.user_id)}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center justify-between ${
                        formData.assignee_id === member.user_id ? 'bg-primary/10 text-primary' : ''
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                          {member.name?.charAt(0).toUpperCase()}
                        </div>
                        {member.name}
                      </span>
                      {member.is_on_shift ? (
                        <span className="flex items-center gap-1 text-[10px] text-emerald-500">
                          <Clock size={10} />
                          On Shift
                        </span>
                      ) : (
                        <span className="text-[10px] text-muted-foreground/50">Off Shift</span>
                      )}
                    </button>
                  ))}
                </>
              )}
              
              {/* Other Teams Section */}
              {assignmentOptions?.other_teams?.length > 0 && (
                <>
                  <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30 flex items-center gap-1.5">
                    <ArrowUpCircle size={10} />
                    Escalate to Team
                  </div>
                  {assignmentOptions.other_teams.map(team => (
                    <button
                      key={team.team_id}
                      onClick={() => handleAssignToTeam(team.team_id)}
                      className="w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center justify-between"
                    >
                      <span className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${
                          team.escalation_level === 'L1' ? 'bg-blue-500' :
                          team.escalation_level === 'L2' ? 'bg-amber-500' : 'bg-red-500'
                        }`} />
                        {team.name}
                        <span className="text-[10px] text-muted-foreground">({team.escalation_level})</span>
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {team.on_shift_count} on shift
                      </span>
                    </button>
                  ))}
                </>
              )}
              
              {/* All users section */}
              {users.length > 0 && (
                <>
                  <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30">
                    {assignmentOptions?.team_members?.length > 0 ? 'Other Users' : 'All Users'}
                  </div>
                  {users
                    .filter(user => {
                      const userId = user.id || user.user_id;
                      if (userId === (currentUser?.user_id || currentUser?.id)) return false;
                      if (assignmentOptions?.team_members?.some(m => m.user_id === userId)) return false;
                      return true;
                    })
                    .map(user => (
                    <button
                      key={user.id || user.user_id}
                      onClick={() => handleAssign(user.id || user.user_id)}
                      className={`w-full px-3 py-2 text-left text-sm hover:bg-secondary/50 flex items-center gap-2 ${
                        formData.assignee_id === (user.id || user.user_id) ? 'bg-primary/10 text-primary' : ''
                      }`}
                    >
                      <div className="w-5 h-5 rounded-full bg-gradient-to-br from-primary/50 to-accent/50 flex items-center justify-center text-[9px] font-medium">
                        {user.name?.charAt(0).toUpperCase()}
                      </div>
                      {user.name}
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        {/* Status - Only show if assigned */}
        {formData.assignee_id && (
          <div>
            <label className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${statusConfig.color}`} />
              Status
            </label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              className="w-full h-8 px-2 text-sm rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-foreground/20 transition-shadow"
              data-testid="drawer-status-select"
            >
              {STATUSES.map(status => (
                <option key={status.value} value={status.value}>{status.label}</option>
              ))}
            </select>
          </div>
        )}

        {/* Priority */}
        <div>
          <label className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
            <AlertCircle size={11} className={priorityConfig.color} />
            Priority
          </label>
          <select
            value={formData.priority}
            onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
            className="w-full h-8 px-2 text-sm rounded-md bg-card border border-border focus:outline-none focus:ring-2 focus:ring-foreground/20 transition-shadow"
            data-testid="drawer-priority-select"
          >
            {PRIORITIES.map(priority => (
              <option key={priority.value} value={priority.value}>{priority.label}</option>
            ))}
          </select>
        </div>


        {/* Ticket Attributes */}
        <div>
          <button
            onClick={() => toggleSection('attributes')}
            className="w-full flex items-center justify-between py-1 group"
          >
            <div className="flex items-center gap-2">
              <Sparkles size={12} className="text-muted-foreground" />
              <span className="text-[11px] font-semibold text-foreground/60 uppercase tracking-wider">Attributes</span>
            </div>
            {sectionsExpanded.attributes ? (
              <ChevronDown size={12} className="text-muted-foreground" />
            ) : (
              <ChevronRight size={12} className="text-muted-foreground" />
            )}
          </button>
          
          {sectionsExpanded.attributes && (
            <div className="mt-1.5 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">ID</span>
                <span className="font-mono text-foreground/80 text-[10px]">
                  {ticket.ticket_id || ticket.id?.slice(-12)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Source</span>
                <span className="capitalize text-foreground/80">{ticket.source || 'manual'}</span>
              </div>
              {ticket.source === 'email' && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Channel</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal-500/15 text-teal-400">Email</span>
                </div>
              )}
              {ticket.source === 'portal' && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Channel</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400">Portal</span>
                </div>
              )}
              {ticket.customer_email && (
                <div className="flex items-center justify-between gap-1">
                  <span className="text-muted-foreground shrink-0">Customer</span>
                  <button
                    onClick={() => { navigator.clipboard.writeText(ticket.customer_email); }}
                    className="text-foreground/80 text-[10px] truncate max-w-[180px] hover:text-primary transition-colors cursor-pointer flex items-center gap-1"
                    title={`${ticket.customer_email} — Click to copy`}
                    data-testid="customer-email-copy"
                  >
                    <span className="truncate">{ticket.customer_email}</span>
                    <Copy size={9} className="shrink-0 opacity-50" />
                  </button>
                </div>
              )}
              {ticket.domain && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Domain</span>
                  <span className="text-foreground/80">{ticket.domain}</span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="text-foreground/80 text-[10px]">
                  {new Date(ticket.created_at).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Age</span>
                <span className="text-foreground/80 text-[10px]">
                  {(() => {
                    const diff = Date.now() - new Date(ticket.created_at).getTime();
                    const mins = Math.floor(diff / 60000);
                    if (mins < 60) return `${mins}m`;
                    const hrs = Math.floor(mins / 60);
                    if (hrs < 24) return `${hrs}h`;
                    const days = Math.floor(hrs / 24);
                    return `${days}d`;
                  })()}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">URL</span>
                <button
                  onClick={handleCopyLink}
                  className="text-[10px] text-primary hover:text-primary/80 hover:underline transition-colors flex items-center gap-1"
                  title="Click to copy URL"
                >
                  <Copy size={10} />
                  Copy URL
                </button>
              </div>
              {ticket.customer_email && (
                <EmailDeliveryStatus ticketId={ticket.ticket_id} />
              )}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="h-px bg-border/30" />

        {/* Tags Section */}
        <div>
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <Tag size={12} className="text-muted-foreground" />
              <span className="text-[11px] font-semibold text-foreground/60 uppercase tracking-wider">Tags</span>
            </div>
            {loadingTags && <Loader2 size={12} className="animate-spin text-muted-foreground" />}
          </div>
          
          {/* Current Tags */}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {ticketTags.map((tag, i) => (
              <span 
                key={i} 
                className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full bg-primary/20 text-primary group"
              >
                #{tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
                  title="Remove tag"
                  data-testid={`remove-tag-${tag}`}
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            {ticketTags.length === 0 && (
              <span className="text-[10px] text-muted-foreground/50 italic">No tags</span>
            )}
          </div>
          
          {/* Add Tag Input */}
          <div className="mt-2 relative">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => {
                setTagInput(e.target.value);
                setShowTagDropdown(true);
              }}
              onFocus={() => setShowTagDropdown(true)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && tagInput.trim()) {
                  e.preventDefault();
                  handleAddTag(tagInput);
                }
                if (e.key === 'Escape') {
                  setShowTagDropdown(false);
                }
              }}
              placeholder="Add tag..."
              className="w-full h-7 px-2 text-xs rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50 placeholder:text-muted-foreground/50"
              data-testid="tag-input"
            />
            
            {/* Tag Dropdown */}
            {showTagDropdown && (tagInput.trim() || filteredTags.length > 0) && (
              <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-lg shadow-lg max-h-40 overflow-y-auto">
                {/* Create new tag option */}
                {tagInput.trim() && !availableTags.includes(tagInput.trim().toLowerCase().replace(/\s+/g, '-')) && (
                  <button
                    onClick={() => handleAddTag(tagInput)}
                    className="w-full px-3 py-2 text-left text-xs hover:bg-primary/10 flex items-center gap-2 text-primary border-b border-border/30"
                    data-testid="create-new-tag"
                  >
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/20">+ Create</span>
                    <span>#{tagInput.trim().toLowerCase().replace(/\s+/g, '-')}</span>
                  </button>
                )}
                
                {/* Existing tags */}
                {filteredTags.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-[10px] font-medium uppercase text-muted-foreground bg-secondary/30">
                      Existing Tags
                    </div>
                    {filteredTags.slice(0, 10).map(tag => (
                      <button
                        key={tag}
                        onClick={() => handleAddTag(tag)}
                        className="w-full px-3 py-2 text-left text-xs hover:bg-secondary/50 flex items-center gap-2"
                        data-testid={`add-tag-${tag}`}
                      >
                        <span className="text-primary">#{tag}</span>
                      </button>
                    ))}
                  </>
                )}
                
                {/* No matches */}
                {tagInput.trim() && filteredTags.length === 0 && availableTags.includes(tagInput.trim().toLowerCase().replace(/\s+/g, '-')) && (
                  <div className="px-3 py-2 text-xs text-muted-foreground">
                    Tag already added
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Click outside to close dropdown */}
          {showTagDropdown && (
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setShowTagDropdown(false)}
            />
          )}
        </div>

        {/* CSAT Section */}
        {ticket?.customer_email && (
          <>
            <div className="h-px bg-border/30" />
            <div>
              <div className="flex items-center justify-between py-1">
                <div className="flex items-center gap-2">
                  <MessageSquareHeart size={12} className="text-muted-foreground" />
                  <span className="text-[11px] font-semibold text-foreground/60 uppercase tracking-wider">Customer Satisfaction</span>
                </div>
              </div>
              
              <div className="mt-2">
                {csatData?.has_response ? (
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map(star => (
                          <Star
                            key={star}
                            size={16}
                            className={star <= csatData.rating 
                              ? 'fill-yellow-400 text-yellow-400' 
                              : 'fill-transparent text-gray-400'
                            }
                          />
                        ))}
                      </div>
                      <span className={`text-xs font-medium ${
                        csatData.rating >= 4 ? 'text-emerald-400' : 
                        csatData.rating >= 3 ? 'text-amber-400' : 'text-red-400'
                      }`}>
                        {csatData.rating}/5
                      </span>
                    </div>
                    {csatData.feedback && (
                      <p className="text-xs text-muted-foreground mt-2 italic">
                        &ldquo;{csatData.feedback}&rdquo;
                      </p>
                    )}
                    <p className="text-[10px] text-muted-foreground/60 mt-2">
                      by {csatData.customer_name} &middot; {new Date(csatData.submitted_at).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                    </p>
                  </div>
                ) : csatData?.survey_sent ? (
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <div className="flex items-center gap-2 text-amber-400">
                      <Mail size={14} />
                      <span className="text-xs font-medium">Survey sent</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Awaiting response &middot; Expires {new Date(csatData.expires_at).toLocaleString('en-US', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })}
                    </p>
                  </div>
                ) : formData.status === 'resolved' ? (
                  <button
                    onClick={handleSendCsat}
                    disabled={sendingCsat}
                    className="w-full py-2 px-3 rounded-lg bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                    data-testid="send-csat-button"
                  >
                    {sendingCsat ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send size={14} />
                        Send CSAT Survey
                      </>
                    )}
                  </button>
                ) : (
                  <p className="text-[10px] text-muted-foreground/60 italic">
                    Resolve ticket to send CSAT survey
                  </p>
                )}
              </div>
            </div>
          </>
        )}

        {/* Custom Fields Section */}
        {customFields.length > 0 && (
          <>
            <div className="h-px bg-border/30" />

            <div>
              <button
                onClick={() => toggleSection('customFields')}
                className="w-full flex items-center justify-between py-1 group"
              >
                <div className="flex items-center gap-2">
                  <Settings size={12} className="text-muted-foreground" />
                  <span className="text-[11px] font-semibold text-foreground/60 uppercase tracking-wider">Custom Fields</span>
                </div>
                {sectionsExpanded.customFields ? (
                  <ChevronDown size={12} className="text-muted-foreground" />
                ) : (
                  <ChevronRight size={12} className="text-muted-foreground" />
                )}
              </button>
              
              {sectionsExpanded.customFields && (
                <div className="mt-2 space-y-3">
                  {customFields.map(field => (
                    <div key={field.field_id}>
                      <label className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider mb-1.5 block">
                        {field.name}
                        {field.required && <span className="text-destructive ml-0.5">*</span>}
                      </label>
                      {field.field_type === 'text' && (
                        <input
                          type="text"
                          value={customFieldValues[field.field_id] || ''}
                          onChange={(e) => setCustomFieldValues(prev => ({ 
                            ...prev, 
                            [field.field_id]: e.target.value 
                          }))}
                          className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                          placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
                          data-testid={`custom-field-${field.field_id}`}
                        />
                      )}
                      {field.field_type === 'number' && (
                        <input
                          type="number"
                          value={customFieldValues[field.field_id] || ''}
                          onChange={(e) => setCustomFieldValues(prev => ({ 
                            ...prev, 
                            [field.field_id]: e.target.value 
                          }))}
                          className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                          placeholder={field.description || `Enter ${field.name.toLowerCase()}`}
                          data-testid={`custom-field-${field.field_id}`}
                        />
                      )}
                      {field.field_type === 'select' && (
                        <select
                          value={customFieldValues[field.field_id] || ''}
                          onChange={(e) => setCustomFieldValues(prev => ({ 
                            ...prev, 
                            [field.field_id]: e.target.value 
                          }))}
                          className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                          data-testid={`custom-field-${field.field_id}`}
                        >
                          <option value="">Select {field.name.toLowerCase()}</option>
                          {field.options?.map((opt, idx) => (
                            <option key={idx} value={opt}>{opt}</option>
                          ))}
                        </select>
                      )}
                      {field.field_type === 'date' && (
                        <input
                          type="date"
                          value={customFieldValues[field.field_id] || ''}
                          onChange={(e) => setCustomFieldValues(prev => ({ 
                            ...prev, 
                            [field.field_id]: e.target.value 
                          }))}
                          className="w-full h-8 px-2 text-sm rounded-md bg-secondary/30 border border-border/30 focus:outline-none focus:ring-1 focus:ring-primary/50"
                          data-testid={`custom-field-${field.field_id}`}
                        />
                      )}
                      {field.field_type === 'boolean' && (
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={customFieldValues[field.field_id] || false}
                            onChange={(e) => setCustomFieldValues(prev => ({ 
                              ...prev, 
                              [field.field_id]: e.target.checked 
                            }))}
                            className="w-4 h-4 rounded border-border text-primary focus:ring-primary/50"
                            data-testid={`custom-field-${field.field_id}`}
                          />
                          <span className="text-xs text-foreground/80">
                            {field.description || 'Yes'}
                          </span>
                        </label>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* Divider */}
        <div className="h-px bg-border/30" />

        {/* Links Section */}
        <div>
          <button
            onClick={() => toggleSection('links')}
            className="w-full flex items-center justify-between py-1 group"
          >
            <div className="flex items-center gap-2">
              <Link2 size={12} className="text-muted-foreground" />
              <span className="text-[11px] font-semibold text-foreground/60 uppercase tracking-wider">Links</span>
              {linkedFeatureRequests.length > 0 && (
                <span className="text-[9px] bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                  {linkedFeatureRequests.length} FR
                </span>
              )}
            </div>
            {sectionsExpanded.links ? (
              <ChevronDown size={12} className="text-muted-foreground" />
            ) : (
              <ChevronRight size={12} className="text-muted-foreground" />
            )}
          </button>
          
          {sectionsExpanded.links && (
            <div className="mt-1.5 space-y-2">
              {/* Linked Feature Requests */}
              {linkedFeatureRequests.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider pl-1">
                    Feature Requests ({linkedFeatureRequests.length})
                  </div>
                  {linkedFeatureRequests.map(fr => (
                    <div 
                      key={fr.feature_request_id}
                      className="flex items-center gap-2 p-2 bg-secondary/30 rounded-md group"
                    >
                      <Bookmark size={12} className={`shrink-0 ${
                        fr.request_type === 'bug_fix' ? 'text-red-400' :
                        fr.request_type === 'enhancement' ? 'text-emerald-400' :
                        'text-blue-400'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                            fr.request_type === 'bug_fix' ? 'bg-red-500/20 text-red-400' :
                            fr.request_type === 'enhancement' ? 'bg-emerald-500/20 text-emerald-400' :
                            'bg-blue-500/20 text-blue-400'
                          }`}>
                            {fr.request_type === 'bug_fix' ? 'Bug Fix' : 
                             fr.request_type === 'enhancement' ? 'Enhancement' : 'Feature'}
                          </span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                            fr.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                            fr.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                            fr.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-gray-500/20 text-gray-400'
                          }`}>
                            {fr.priority}
                          </span>
                        </div>
                        <div className="text-xs text-foreground truncate mt-0.5" title={fr.title}>
                          {fr.title}
                        </div>
                        <div className="text-[10px] text-muted-foreground font-mono">
                          {fr.feature_request_id}
                        </div>
                      </div>
                      <button
                        onClick={() => handleUnlinkFeatureRequest(fr.feature_request_id)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                        title="Unlink feature request"
                      >
                        <X size={12} className="text-red-400" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Add Feature Request Link */}
              <button
                onClick={() => setShowFeatureRequestModal(true)}
                className="w-full flex items-center justify-between py-1 pl-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Bookmark size={11} />
                  Link Feature Request
                </span>
                <span className="text-primary text-[10px]">+ Add</span>
              </button>
              
              <div className="h-px bg-border/20" />
              
              {/* Linked Tickets Section */}
              <div className="space-y-1.5">
                <div className="text-[11px] text-foreground/60 font-semibold uppercase tracking-wider pl-1">
                  Linked Tickets ({linkedTickets.length})
                </div>
                
                {linkedTickets.length > 0 ? (
                  <div className="space-y-1">
                    {linkedTickets.map(link => {
                      const getLinkTypeStyle = (type) => {
                        switch (type) {
                          case 'split_from':
                            return { icon: Scissors, color: 'text-violet-400', bg: 'bg-violet-500/10', label: 'Split from' };
                          case 'split_to':
                            return { icon: Scissors, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Split to' };
                          case 'blocks':
                            return { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Blocks' };
                          case 'blocked_by':
                            return { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Blocked by' };
                          case 'duplicates':
                            return { icon: Copy, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Duplicates' };
                          default:
                            return { icon: Link2, color: 'text-primary', bg: 'bg-primary/10', label: 'Related' };
                        }
                      };
                      const style = getLinkTypeStyle(link.link_type);
                      const IconComponent = style.icon;
                      
                      return (
                        <div 
                          key={link.ticket_id}
                          className={`flex items-center gap-2 p-2 ${style.bg} rounded-md group cursor-pointer hover:opacity-80 transition-opacity`}
                          onClick={() => {
                            window.open(`/all-tickets?ticket=${link.ticket_id}`, '_blank');
                          }}
                          data-testid={`linked-ticket-${link.ticket_id}`}
                        >
                          <IconComponent size={12} className={`shrink-0 ${style.color}`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${style.bg} ${style.color}`}>
                                {style.label}
                              </span>
                            </div>
                            <div className="text-xs text-foreground truncate mt-0.5" title={link.title}>
                              {link.title || link.ticket_id}
                            </div>
                            <div className="text-[10px] text-muted-foreground font-mono">
                              {link.ticket_id}
                            </div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUnlinkTicket(link.ticket_id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                            title="Unlink ticket"
                          >
                            <X size={12} className="text-red-400" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-[11px] text-muted-foreground/60 pl-1">
                    No linked tickets
                  </div>
                )}
                
                {/* Add link button */}
                <button
                  onClick={() => setShowLinkModal(true)}
                  className="w-full flex items-center justify-between py-1 pl-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                  data-testid="add-link-button"
                >
                  <span className="flex items-center gap-1.5">
                    <Link2 size={11} />
                    Link Ticket
                  </span>
                  <span className="text-primary text-[10px]">+ Add</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="h-px bg-border/30" />
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-card border border-border rounded-lg p-4 shadow-lg max-w-sm mx-4">
            <h3 className="text-sm font-medium mb-2">Delete Ticket?</h3>
            <p className="text-xs text-muted-foreground mb-4">
              This action cannot be undone. The ticket and all its messages will be permanently deleted.
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 h-8 px-3 text-xs border border-border/40 rounded hover:bg-secondary/50 transition-colors"
                data-testid="drawer-delete-cancel-button"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 h-8 px-3 text-xs font-medium bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
                data-testid="drawer-delete-confirm-button"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TicketDetailsPanel;
