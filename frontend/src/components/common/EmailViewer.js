import React, { useMemo, useState } from 'react';
import { Image, MoreHorizontal } from 'lucide-react';
import ImageGallery from './ImageGallery';
import { splitQuotedContent } from '../tickets/EmailMessage';

/**
 * EmailViewer - Ultra-compact email content viewer
 * Maximum text density, minimal chrome
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
      if (src && 
          !src.includes('tracking') && 
          !src.includes('pixel') &&
          !src.includes('spacer') &&
          !src.includes('1x1') &&
          !src.startsWith('data:image/gif')
      ) {
        const altMatch = match[0].match(/alt=["']([^"']+)["']/i);
        images.push({
          src,
          alt: altMatch ? altMatch[1] : 'Image'
        });
      }
    }
    
    return images.filter((img, index, self) => 
      index === self.findIndex(i => i.src === img.src)
    ).slice(0, 20); // Allow more images since gallery handles them well
  }, [ticket?.email_html]);
  
  // Convert HTML to clean plain text
  const getCleanText = useMemo(() => {
    if (ticket?.email_text) {
      return ticket.email_text;
    }
    
    if (ticket?.email_html) {
      let text = ticket.email_html;
      text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
      text = text.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
      text = text.replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '');
      text = text.replace(/<\/?(p|div|br|tr|li|h[1-6])[^>]*>/gi, '\n');
      text = text.replace(/<[^>]+>/g, '');
      text = text.replace(/&nbsp;/gi, ' ');
      text = text.replace(/&amp;/gi, '&');
      text = text.replace(/&lt;/gi, '<');
      text = text.replace(/&gt;/gi, '>');
      text = text.replace(/&quot;/gi, '"');
      text = text.replace(/&#39;/gi, "'");
      text = text.replace(/&[#\w]+;/gi, '');
      text = text.replace(/[ \t]+/g, ' ');
      text = text.replace(/\n[ \t]+/g, '\n');
      text = text.replace(/[ \t]+\n/g, '\n');
      text = text.replace(/\n{3,}/g, '\n\n');
      return text.trim();
    }
    
    return ticket?.description || '';
  }, [ticket?.email_html, ticket?.email_text, ticket?.description]);
  
  // Format plain text with collapsible quoted content
  const formatPlainText = (text) => {
    if (!text) return <span className="text-muted-foreground/60">No content</span>;
    
    const { visible, quoted } = splitQuotedContent(text);
    
    const renderLines = (str) => {
      const lines = str.split('\n');
      const elements = [];
      let lastWasEmpty = false;
      
      lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        
        if (!trimmedLine) {
          if (!lastWasEmpty && elements.length > 0) {
            elements.push(<div key={`space-${index}`} className="h-px" />);
            lastWasEmpty = true;
          }
        } else {
          elements.push(<div key={index}>{trimmedLine}</div>);
          lastWasEmpty = false;
        }
      });
      
      return elements.length > 0 ? elements : null;
    };

    return (
      <>
        {renderLines(visible) || <span className="text-muted-foreground/60">No content</span>}
        {quoted && <CollapsibleEmailQuote quoted={quoted} />}
      </>
    );
  };

  const CollapsibleEmailQuote = ({ quoted }) => {
    const [expanded, setExpanded] = useState(false);
    if (!quoted) return null;
    return expanded ? (
      <div className="mt-1 pt-1 border-t border-border/10">
        <div className="text-muted-foreground/50 text-[11px] leading-snug whitespace-pre-wrap">{quoted}</div>
        <button onClick={() => setExpanded(false)} className="text-[10px] text-muted-foreground/30 hover:text-muted-foreground/50 mt-0.5">hide</button>
      </div>
    ) : (
      <button
        onClick={() => setExpanded(true)}
        className="mt-0.5 text-muted-foreground/25 hover:text-muted-foreground/40 transition-colors"
        title="Show quoted text"
        data-testid="show-quoted-text"
      >
        <MoreHorizontal size={14} />
      </button>
    );
  };
  
  return (
    <div className={`email-viewer ${className}`}>
      {/* Plain text content - ultra tight with proper word wrapping */}
      <div className="text-[12px] text-foreground/90 leading-snug" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
        {formatPlainText(getCleanText)}
      </div>
      
      {/* Image Gallery */}
      {extractedImages.length > 0 && (
        <div className="mt-2 pt-1.5 border-t border-border/20">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-1.5">
            <Image size={10} />
            <span>{extractedImages.length} image{extractedImages.length !== 1 ? 's' : ''}</span>
          </div>
          <ImageGallery images={extractedImages} />
        </div>
      )}
    </div>
  );
};

export default EmailViewer;
