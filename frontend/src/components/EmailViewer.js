import React, { useMemo } from 'react';
import { Image, ExternalLink } from 'lucide-react';

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
    ).slice(0, 10);
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
  
  // Format plain text - ultra compact
  const formatPlainText = (text) => {
    if (!text) return <span className="text-muted-foreground/60">No content</span>;
    
    const lines = text.split('\n');
    const elements = [];
    let quoteBuffer = [];
    let lastWasEmpty = false;
    
    const flushQuoteBuffer = () => {
      if (quoteBuffer.length > 0) {
        elements.push(
          <blockquote 
            key={`quote-${elements.length}`} 
            className="my-1 pl-2 border-l border-muted-foreground/30 text-muted-foreground/60 text-[12px] leading-tight"
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
      const isReplyHeader = /^On .+ wrote:$/i.test(trimmedLine) || 
                            /^-{3,}\s*(Original Message|Forwarded message)\s*-{3,}$/i.test(trimmedLine) ||
                            /^From:.*@.*$/i.test(trimmedLine) && index > 5;
      
      if (isQuoted) {
        quoteBuffer.push(line);
      } else if (isReplyHeader) {
        flushQuoteBuffer();
        elements.push(
          <div key={`header-${index}`} className="my-1.5 pt-1 text-[10px] text-muted-foreground/40 border-t border-border/20">
            {trimmedLine}
          </div>
        );
      } else if (!trimmedLine) {
        flushQuoteBuffer();
        if (!lastWasEmpty && elements.length > 0) {
          elements.push(<div key={`space-${index}`} className="h-1" />);
          lastWasEmpty = true;
        }
      } else {
        flushQuoteBuffer();
        elements.push(<div key={index}>{trimmedLine}</div>);
        lastWasEmpty = false;
      }
    });
    
    flushQuoteBuffer();
    return elements.length > 0 ? elements : <span className="text-muted-foreground/60">No content</span>;
  };
  
  return (
    <div className={`email-viewer ${className}`}>
      {/* Plain text content - ultra tight with proper word wrapping */}
      <div className="text-[13px] text-foreground/90 leading-tight" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
        {formatPlainText(getCleanText)}
      </div>
      
      {/* Extracted images as small thumbnails */}
      {extractedImages.length > 0 && (
        <div className="mt-2 pt-1.5 border-t border-border/20">
          <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-1">
            <Image size={10} />
            <span>{extractedImages.length} images</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {extractedImages.map((img, index) => (
              <a
                key={index}
                href={img.src}
                target="_blank"
                rel="noopener noreferrer"
                className="w-10 h-10 rounded overflow-hidden bg-secondary/30 border border-border/20 hover:border-primary/40"
                title={img.alt}
              >
                <img 
                  src={img.src} 
                  alt={img.alt}
                  className="w-full h-full object-cover"
                  onError={(e) => e.target.style.display = 'none'}
                />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailViewer;
