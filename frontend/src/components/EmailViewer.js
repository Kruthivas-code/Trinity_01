import React, { useState, useRef, useEffect } from 'react';
import { Mail, Eye, EyeOff, ExternalLink, Maximize2, Minimize2 } from 'lucide-react';
import DOMPurify from 'dompurify';

/**
 * EmailViewer - Production-grade email content viewer
 * 
 * Features:
 * - Safe HTML rendering with DOMPurify
 * - Toggle between HTML and plain text view
 * - Image loading control
 * - Responsive iframe for complex email layouts
 * - External link handling
 */
const EmailViewer = ({ 
  ticket, 
  className = '' 
}) => {
  const [viewMode, setViewMode] = useState('html'); // 'html' | 'text'
  const [loadImages, setLoadImages] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const iframeRef = useRef(null);
  
  const hasHtml = !!ticket?.email_html;
  const hasText = !!ticket?.email_text;
  
  // Configure DOMPurify for email content
  const sanitizeHtml = (html) => {
    if (!html) return '';
    
    // Configure DOMPurify
    const config = {
      ALLOWED_TAGS: [
        'p', 'br', 'b', 'i', 'u', 'strong', 'em', 'a', 'img', 
        'div', 'span', 'table', 'tr', 'td', 'th', 'tbody', 'thead',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'pre', 'code', 'hr', 'center', 'font',
        'style', 'head', 'body', 'html'
      ],
      ALLOWED_ATTR: [
        'href', 'src', 'alt', 'title', 'class', 'id', 'style',
        'width', 'height', 'align', 'valign', 'bgcolor', 'color',
        'border', 'cellpadding', 'cellspacing', 'target', 'rel',
        'colspan', 'rowspan', 'face', 'size'
      ],
      ALLOW_DATA_ATTR: false,
      ADD_ATTR: ['target'],
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
      FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover']
    };
    
    let sanitized = DOMPurify.sanitize(html, config);
    
    // Add target="_blank" to all links for safety
    sanitized = sanitized.replace(/<a /g, '<a target="_blank" rel="noopener noreferrer" ');
    
    // If images should not load, replace src with data-src
    if (!loadImages) {
      sanitized = sanitized.replace(/(<img[^>]*)\ssrc=/gi, '$1 data-blocked-src=');
    }
    
    return sanitized;
  };
  
  // Wrap HTML content with email-friendly styles
  const getStyledHtml = () => {
    const sanitized = sanitizeHtml(ticket?.email_html);
    
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          * {
            box-sizing: border-box;
          }
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.5;
            color: #333;
            margin: 0;
            padding: 16px;
            background: transparent;
            word-wrap: break-word;
            overflow-wrap: break-word;
          }
          img {
            max-width: 100%;
            height: auto;
          }
          a {
            color: #2563eb;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
          table {
            max-width: 100%;
            border-collapse: collapse;
          }
          blockquote {
            margin: 10px 0;
            padding: 10px 20px;
            border-left: 3px solid #ddd;
            color: #666;
            background: #f9f9f9;
          }
          pre, code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 13px;
          }
          pre {
            padding: 12px;
            overflow-x: auto;
          }
          /* Hide tracking pixels */
          img[width="1"], img[height="1"] {
            display: none !important;
          }
        </style>
      </head>
      <body>
        ${sanitized}
      </body>
      </html>
    `;
  };
  
  // Adjust iframe height to content
  useEffect(() => {
    if (iframeRef.current && viewMode === 'html' && hasHtml) {
      const iframe = iframeRef.current;
      
      const adjustHeight = () => {
        try {
          const doc = iframe.contentDocument || iframe.contentWindow?.document;
          if (doc && doc.body) {
            const height = Math.max(
              doc.body.scrollHeight,
              doc.documentElement.scrollHeight,
              200 // minimum height
            );
            iframe.style.height = Math.min(height, isExpanded ? 2000 : 500) + 'px';
          }
        } catch (e) {
          // Cross-origin issues - use default height
          iframe.style.height = isExpanded ? '800px' : '400px';
        }
      };
      
      iframe.onload = adjustHeight;
      // Also adjust after images load
      setTimeout(adjustHeight, 500);
    }
  }, [viewMode, hasHtml, ticket?.email_html, loadImages, isExpanded]);
  
  // Format plain text with proper quote handling for email threads
  const formatPlainText = (text) => {
    if (!text) return 'No content';
    
    // Split into lines and process
    const lines = text.split('\n');
    const elements = [];
    let quoteBuffer = [];
    
    const flushQuoteBuffer = () => {
      if (quoteBuffer.length > 0) {
        elements.push(
          <blockquote 
            key={`quote-${elements.length}`} 
            className="my-2 pl-3 py-1 border-l-2 border-muted-foreground/40 text-muted-foreground/80 text-sm bg-muted/20 rounded-r"
          >
            {quoteBuffer.map((line, i) => (
              <div key={i} className="leading-relaxed">{line.replace(/^>+\s*/, '')}</div>
            ))}
          </blockquote>
        );
        quoteBuffer = [];
      }
    };
    
    lines.forEach((line, index) => {
      const isQuoted = /^>+/.test(line.trimStart());
      
      // Check for common reply header patterns
      const isReplyHeader = /^On .+ wrote:$/i.test(line.trim()) || 
                            /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}.+wrote:?$/i.test(line.trim()) ||
                            /^.+<.+@.+>.+wrote:?$/i.test(line.trim()) ||
                            /^-{3,}\s*Original Message\s*-{3,}$/i.test(line.trim()) ||
                            /^From:.*$/i.test(line.trim()) && index > 0;
      
      if (isQuoted) {
        quoteBuffer.push(line);
      } else if (isReplyHeader) {
        flushQuoteBuffer();
        elements.push(
          <div key={`header-${index}`} className="my-3 py-2 text-xs text-muted-foreground/60 border-t border-border/30 italic">
            {line}
          </div>
        );
      } else {
        flushQuoteBuffer();
        if (line.trim()) {
          elements.push(<div key={index} className="leading-relaxed">{line}</div>);
        } else if (elements.length > 0) {
          elements.push(<div key={index} className="h-2" />);
        }
      }
    });
    
    flushQuoteBuffer();
    return elements.length > 0 ? elements : 'No content';
  };
  
  // If no email content, show description
  if (!hasHtml && !hasText) {
    return (
      <div className={`text-sm text-muted-foreground ${className}`}>
        {ticket?.description || 'No content available'}
      </div>
    );
  }
  
  return (
    <div className={`email-viewer ${className}`}>
      {/* Controls */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-border/30">
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          {hasHtml && hasText && (
            <div className="flex items-center bg-secondary/50 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('html')}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  viewMode === 'html' 
                    ? 'bg-background text-foreground shadow-sm' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Rich
              </button>
              <button
                onClick={() => setViewMode('text')}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  viewMode === 'text' 
                    ? 'bg-background text-foreground shadow-sm' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Plain
              </button>
            </div>
          )}
          
          {/* Source indicator */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Mail size={12} />
            <span>Email</span>
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Image Loading Toggle */}
          {hasHtml && viewMode === 'html' && (
            <button
              onClick={() => setLoadImages(!loadImages)}
              className={`p-1.5 rounded-md transition-colors ${
                loadImages 
                  ? 'text-foreground bg-secondary/50' 
                  : 'text-muted-foreground hover:bg-secondary/30'
              }`}
              title={loadImages ? 'Hide images' : 'Show images'}
            >
              {loadImages ? <Eye size={14} /> : <EyeOff size={14} />}
            </button>
          )}
          
          {/* Expand Toggle */}
          {hasHtml && viewMode === 'html' && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 rounded-md text-muted-foreground hover:bg-secondary/30 transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className={`rounded-lg overflow-hidden ${isExpanded ? '' : 'max-h-[500px] overflow-y-auto'}`}>
        {viewMode === 'html' && hasHtml ? (
          <iframe
            ref={iframeRef}
            srcDoc={getStyledHtml()}
            className="w-full border-0 bg-white rounded-lg"
            style={{ minHeight: '200px', height: '400px' }}
            sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            title="Email content"
          />
        ) : (
          <div className="p-4 bg-secondary/20 rounded-lg">
            <pre className="whitespace-pre-wrap text-sm text-foreground font-sans leading-relaxed">
              {ticket?.email_text || ticket?.description || 'No content'}
            </pre>
          </div>
        )}
      </div>
      
      {/* Email metadata */}
      {ticket?.email_sender && (
        <div className="mt-3 pt-2 border-t border-border/30 text-xs text-muted-foreground space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium w-12">From:</span>
            <span className="truncate">{ticket.email_sender}</span>
          </div>
          {ticket.email_to && (
            <div className="flex items-center gap-2">
              <span className="font-medium w-12">To:</span>
              <span className="truncate">{ticket.email_to}</span>
            </div>
          )}
          {ticket.email_date && (
            <div className="flex items-center gap-2">
              <span className="font-medium w-12">Date:</span>
              <span>{ticket.email_date}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EmailViewer;
