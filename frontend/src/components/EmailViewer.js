import React, { useMemo } from 'react';
import { Image, ExternalLink } from 'lucide-react';

/**
 * EmailViewer - Clean, minimal email content viewer
 * 
 * Features:
 * - Always plain text display (no HTML/CSS leakage)
 * - Extracts images from HTML and shows as attachments
 * - Clean quote handling for email threads
 */
const EmailViewer = ({ 
  ticket, 
  className = '' 
}) => {
  
  // Extract image URLs from HTML content
  const extractedImages = useMemo(() => {
    if (!ticket?.email_html) return [];
    
    const images = [];
    const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
    let match;
    
    while ((match = imgRegex.exec(ticket.email_html)) !== null) {
      const src = match[1];
      // Filter out tracking pixels and tiny images
      if (src && 
          !src.includes('tracking') && 
          !src.includes('pixel') &&
          !src.includes('spacer') &&
          !src.includes('1x1') &&
          !src.startsWith('data:image/gif') // Often tracking
      ) {
        // Try to get alt text
        const altMatch = match[0].match(/alt=["']([^"']+)["']/i);
        images.push({
          src,
          alt: altMatch ? altMatch[1] : 'Image'
        });
      }
    }
    
    // Deduplicate by src
    return images.filter((img, index, self) => 
      index === self.findIndex(i => i.src === img.src)
    ).slice(0, 10); // Limit to 10 images
  }, [ticket?.email_html]);
  
  // Convert HTML to clean plain text
  const getCleanText = useMemo(() => {
    // Prefer email_text if available
    if (ticket?.email_text) {
      return ticket.email_text;
    }
    
    // Convert HTML to text
    if (ticket?.email_html) {
      let text = ticket.email_html;
      
      // Remove style tags and their content
      text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
      
      // Remove script tags
      text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
      
      // Remove head section
      text = text.replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '');
      
      // Convert common block elements to newlines
      text = text.replace(/<\/?(p|div|br|tr|li|h[1-6])[^>]*>/gi, '\n');
      
      // Remove all remaining HTML tags
      text = text.replace(/<[^>]+>/g, '');
      
      // Decode HTML entities
      text = text.replace(/&nbsp;/gi, ' ');
      text = text.replace(/&amp;/gi, '&');
      text = text.replace(/&lt;/gi, '<');
      text = text.replace(/&gt;/gi, '>');
      text = text.replace(/&quot;/gi, '"');
      text = text.replace(/&#39;/gi, "'");
      text = text.replace(/&[#\w]+;/gi, ''); // Remove other entities
      
      // Clean up whitespace
      text = text.replace(/[ \t]+/g, ' '); // Multiple spaces to single
      text = text.replace(/\n[ \t]+/g, '\n'); // Remove leading spaces on lines
      text = text.replace(/[ \t]+\n/g, '\n'); // Remove trailing spaces on lines
      text = text.replace(/\n{3,}/g, '\n\n'); // Max 2 newlines
      
      return text.trim();
    }
    
    return ticket?.description || '';
  }, [ticket?.email_html, ticket?.email_text, ticket?.description]);
  
  // Format plain text with proper quote handling
  const formatPlainText = (text) => {
    if (!text) return <span className="text-muted-foreground">No content</span>;
    
    const lines = text.split('\n');
    const elements = [];
    let quoteBuffer = [];
    let lastWasEmpty = false;
    
    const flushQuoteBuffer = () => {
      if (quoteBuffer.length > 0) {
        elements.push(
          <blockquote 
            key={`quote-${elements.length}`} 
            className="my-2 pl-3 py-1 border-l-2 border-muted-foreground/30 text-muted-foreground/70 text-[13px]"
          >
            {quoteBuffer.map((line, i) => (
              <div key={i}>{line.replace(/^>+\s*/, '')}</div>
            ))}
          </blockquote>
        );
        quoteBuffer = [];
      }
    };
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      const isQuoted = /^>+/.test(line.trimStart());
      
      // Check for reply header patterns
      const isReplyHeader = /^On .+ wrote:$/i.test(trimmedLine) || 
                            /^-{3,}\s*(Original Message|Forwarded message)\s*-{3,}$/i.test(trimmedLine) ||
                            /^From:.*@.*$/i.test(trimmedLine) && index > 5;
      
      if (isQuoted) {
        quoteBuffer.push(line);
      } else if (isReplyHeader) {
        flushQuoteBuffer();
        elements.push(
          <div key={`header-${index}`} className="my-3 pt-2 text-xs text-muted-foreground/50 border-t border-border/20">
            {trimmedLine}
          </div>
        );
      } else if (!trimmedLine) {
        flushQuoteBuffer();
        if (!lastWasEmpty && elements.length > 0) {
          elements.push(<div key={`space-${index}`} className="h-2" />);
          lastWasEmpty = true;
        }
      } else {
        flushQuoteBuffer();
        elements.push(<div key={index}>{trimmedLine}</div>);
        lastWasEmpty = false;
      }
    });
    
    flushQuoteBuffer();
    return elements.length > 0 ? elements : <span className="text-muted-foreground">No content</span>;
  };
  
  return (
    <div className={`email-viewer ${className}`}>
      {/* Plain text content */}
      <div className="text-sm text-foreground leading-relaxed">
        {formatPlainText(getCleanText)}
      </div>
      
      {/* Extracted images as attachments */}
      {extractedImages.length > 0 && (
        <div className="mt-4 pt-3 border-t border-border/30">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-2">
            <Image size={12} />
            <span>Attachments ({extractedImages.length})</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {extractedImages.map((img, index) => (
              <a
                key={index}
                href={img.src}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative w-16 h-16 rounded-md overflow-hidden bg-secondary/50 border border-border/30 hover:border-primary/50 transition-colors"
                title={img.alt}
              >
                <img 
                  src={img.src} 
                  alt={img.alt}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'flex';
                  }}
                />
                <div className="hidden absolute inset-0 items-center justify-center bg-secondary/80 text-muted-foreground">
                  <Image size={16} />
                </div>
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <ExternalLink size={14} className="text-white drop-shadow" />
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailViewer;
