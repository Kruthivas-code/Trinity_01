import React from 'react';
import DOMPurify from 'dompurify';
import { GitMerge, BookOpen } from 'lucide-react';
import { renderTextWithMentions } from '../common/MentionInput';
import EmailViewer from '../common/EmailViewer';

// --- Avatar utilities ---

// Curated palette harmonizing with brand teal (#00A1B2)
// Cool-dominant with 2 warm accents — professional, scannable in light + dark
const AVATAR_PALETTE = [
  '#0891b2', // Cyan (brand family)
  '#2563eb', // Blue
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#0d9488', // Teal
  '#059669', // Emerald
  '#d97706', // Amber (warm accent)
  '#be185d', // Rose (warm accent)
];

const hashName = (str) => {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h) + str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
};

export const getAvatarColor = (name) => {
  if (!name) return AVATAR_PALETTE[0];
  return AVATAR_PALETTE[hashName(name) % AVATAR_PALETTE.length];
};

export const getInitials = (name) => {
  if (!name) return '?';
  const display = name.includes('@') ? name.split('@')[0] : name;
  const parts = display.trim().split(/[\s._-]+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }
  return parts[0]?.charAt(0)?.toUpperCase() || '?';
};

const hexToRgba = (hex, alpha) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

// --- Merge color palette for visual distinction of merged ticket sources ---
export const MERGE_COLORS = [
  { bg: 'bg-cyan-500/10', border: 'border-l-cyan-500', text: 'text-cyan-400', label: 'Cyan' },
  { bg: 'bg-amber-500/10', border: 'border-l-amber-500', text: 'text-amber-400', label: 'Amber' },
  { bg: 'bg-violet-500/10', border: 'border-l-violet-500', text: 'text-violet-400', label: 'Violet' },
  { bg: 'bg-emerald-500/10', border: 'border-l-emerald-500', text: 'text-emerald-400', label: 'Emerald' },
  { bg: 'bg-rose-500/10', border: 'border-l-rose-500', text: 'text-rose-400', label: 'Rose' },
];

export const getMergeColor = (colorIndex) => {
  return MERGE_COLORS[colorIndex % MERGE_COLORS.length];
};

// Strip HTML for plain text display
export const stripHtml = (html) => {
  if (!html) return '';
  // Remove style tags and their content
  let text = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
  // Remove script tags
  text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
  // Remove HTML tags
  text = text.replace(/<[^>]*>/g, ' ');
  // Remove CSS properties that might be in text
  text = text.replace(/[\w-]+\s*:\s*[^;]+;/g, ' ');
  // Decode common HTML entities
  text = text.replace(/&nbsp;/g, ' ')
             .replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'")
             .replace(/&#\d+;/g, ' ');
  // Remove multiple spaces and trim
  return text.replace(/\s+/g, ' ').trim();
};

// Email-style message component with merge support
const EmailMessage = ({ type, sender, senderEmail, subject, content, timestamp, isFirst, isAgentMessage, originalTicketId, mergeColorIndex, isMergeDivider, mergedTicketTitle, currentTicketId, emailData, source, onSaveToKB }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { 
      timeZone: 'Asia/Kolkata',
      month: 'short', 
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  // Handle merge divider - clear section header for merged ticket messages
  if (isMergeDivider || type === 'merge_divider') {
    const mergeColor = getMergeColor(mergeColorIndex || 0);
    return (
      <div className="my-4" data-testid="merge-divider">
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${mergeColor.bg} border ${mergeColor.border.replace('border-l-', 'border-')}`}>
          <GitMerge size={14} className={mergeColor.text} />
          <div className="flex-1 min-w-0">
            <span className={`text-xs font-medium ${mergeColor.text}`}>
              Messages from merged ticket
            </span>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="font-mono">{originalTicketId}</span>
              {mergedTicketTitle && (
                <span className="truncate">· {mergedTicketTitle}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Handle system messages (assignments, status changes, etc.) - minimal one-line display
  if (type === 'system') {
    return (
      <div className="flex items-center justify-center py-1">
        <span className="text-[11px] text-muted-foreground/60">
          {content} • {formatDate(timestamp)}
        </span>
      </div>
    );
  }

  const isNote = type === 'internal_note';
  const isReply = type === 'reply';
  const isCustomerMessage = type === 'original' || type === 'customer_reply';
  const isAgent = isAgentMessage || isReply || isNote;
  
  // Check if this message is from a merged ticket (different from current)
  const isFromMergedTicket = originalTicketId && originalTicketId !== currentTicketId;
  const mergeColor = isFromMergedTicket ? getMergeColor(mergeColorIndex || 0) : null;
  
  // Render HTML content safely, with mention support for notes
  const renderContent = (html) => {
    if (!html) return <span className="text-muted-foreground/50 italic">No content</span>;
    
    // For internal notes, render mentions
    if (isNote) {
      // Check for mention format: @[Name](id)
      const hasMentions = /@\[([^\]]+)\]\(([^)]+)\)/.test(html);
      if (hasMentions) {
        return (
          <p className="whitespace-pre-wrap">
            {renderTextWithMentions(html)}
          </p>
        );
      }
    }
    
    // Check if content is HTML or plain text
    const hasHtml = /<[^>]+>/.test(html);
    if (hasHtml) {
      // Sanitize HTML to prevent XSS attacks
      const sanitizedHtml = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'u', 'strong', 'em', 'a', 'ul', 'ol', 'li', 
                       'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                       'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'class', 'style', 'target', 'rel'],
        ALLOW_DATA_ATTR: false
      });
      return (
        <div 
          className="prose prose-sm dark:prose-invert max-w-none
            [&_a]:text-primary [&_a]:underline
            [&_blockquote]:border-l-2 [&_blockquote]:border-primary/30 [&_blockquote]:pl-3 [&_blockquote]:italic
            [&_pre]:bg-secondary/50 [&_pre]:rounded [&_pre]:p-2 [&_pre]:text-xs [&_pre]:overflow-x-auto
            [&_code]:bg-secondary/50 [&_code]:rounded [&_code]:px-1 [&_code]:text-xs
            [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:my-1
            [&_ol]:list-decimal [&_ol]:pl-4 [&_ol]:my-1
            [&_p]:my-1 [&_br]:my-0.5
            [&_img]:max-w-full [&_img]:rounded"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />
      );
    }
    return <p className="whitespace-pre-wrap">{html}</p>;
  };

  // Determine styling based on message type
  const getMessageStyles = () => {
    if (isNote) {
      return {
        container: 'bg-amber-500/10 border border-amber-400/30 rounded-lg',
        alignment: 'mx-auto max-w-[90%]',
        badge: 'bg-amber-400/20 text-amber-400'
      };
    }
    if (isAgent || isReply) {
      return {
        container: 'bg-primary/10 border border-primary/20 rounded-lg rounded-tr-sm',
        alignment: 'ml-auto max-w-[85%]',
        badge: 'bg-primary/20 text-primary'
      };
    }
    return {
      container: 'bg-secondary/30 border border-border/40 rounded-lg rounded-tl-sm',
      alignment: 'mr-auto max-w-[85%]',
      badge: null
    };
  };

  const styles = getMessageStyles();
  
  // More pronounced styling for merged messages - background tint + left border
  const mergeStyles = isFromMergedTicket 
    ? `${mergeColor.bg} border-l-4 ${mergeColor.border}` 
    : '';
  
  return (
    <div className={`${styles.alignment}`} data-testid="message-item">
      <div className={`${styles.container} ${mergeStyles} px-2 py-1.5`}>
        {/* Merged ticket indicator */}
        {isFromMergedTicket && (
          <div className={`flex items-center gap-1 mb-1 text-[9px] ${mergeColor.text}`}>
            <GitMerge size={9} />
            <span className="font-mono">{originalTicketId}</span>
          </div>
        )}
        {/* Message Header - Compact: avatar + sender + timestamp inline */}
        <div className={`flex items-center gap-2 mb-1.5 ${isAgent && !isNote ? 'flex-row-reverse' : ''}`}>
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-semibold shrink-0"
            style={{
              backgroundColor: hexToRgba(getAvatarColor(sender), 0.15),
              color: getAvatarColor(sender),
            }}
            data-testid="message-avatar"
          >
            {getInitials(sender)}
          </div>
          <span className="font-medium text-sm">{sender || 'Unknown'}</span>
          {isNote && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">Note</span>
          )}
          {isReply && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">Reply</span>
          )}
          {isCustomerMessage && source === 'email' && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal-100 text-teal-700" data-testid="source-email-badge">via email</span>
          )}
          {isCustomerMessage && (!source || source === 'portal') && !isFirst && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500" data-testid="source-portal-badge">via portal</span>
          )}
          {source === 'atlas' && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700" data-testid="source-atlas-badge">via Atlas</span>
          )}
          <span className="text-[11px] text-muted-foreground ml-auto shrink-0 tabular-nums">
            {formatDate(timestamp)}
          </span>
        </div>
        
        {/* Message Body */}
        <div className="text-[14px] text-foreground leading-relaxed pl-8">
          {emailData && (emailData.email_html || emailData.email_text) ? (
            <EmailViewer ticket={emailData} />
          ) : (
            renderContent(content)
          )}
        </div>
        {/* Save to KB for agent messages */}
        {isAgent && !isNote && onSaveToKB && content && (
          <div className="pl-8 mt-1">
            <button
              onClick={() => onSaveToKB(content, subject)}
              className="flex items-center gap-1 text-[10px] text-muted-foreground/60 hover:text-primary transition-colors"
              data-testid="save-to-kb-btn"
            >
              <BookOpen size={10} />
              Save to KB
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailMessage;
