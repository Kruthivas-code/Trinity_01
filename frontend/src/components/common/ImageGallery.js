import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download, RotateCcw } from 'lucide-react';

/**
 * ImageGallery - WhatsApp-style image gallery with lightbox
 * 
 * Features:
 * - Grid thumbnails with "+N more" badge
 * - Full-screen lightbox overlay
 * - Thumbnail strip navigation
 * - Zoom in/out with mouse wheel
 * - Keyboard navigation (ESC, arrows)
 * - Download option
 */

const ImageGallery = ({ images = [] }) => {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const imageRef = useRef(null);
  const containerRef = useRef(null);
  
  const MAX_VISIBLE = 4;
  const visibleImages = images.slice(0, MAX_VISIBLE);
  const hiddenCount = Math.max(0, images.length - MAX_VISIBLE);
  
  // Reset zoom and pan when changing images
  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [currentIndex]);
  
  // Keyboard navigation
  useEffect(() => {
    if (!lightboxOpen) return;
    
    const handleKeyDown = (e) => {
      switch (e.key) {
        case 'Escape':
          setLightboxOpen(false);
          break;
        case 'ArrowLeft':
          goToPrevious();
          break;
        case 'ArrowRight':
          goToNext();
          break;
        case '+':
        case '=':
          handleZoomIn();
          break;
        case '-':
          handleZoomOut();
          break;
        case '0':
          resetZoom();
          break;
        default:
          break;
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxOpen, currentIndex, images.length]);
  
  // Prevent body scroll when lightbox is open
  useEffect(() => {
    if (lightboxOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [lightboxOpen]);
  
  const openLightbox = (index) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  
  const goToPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
  }, [images.length]);
  
  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
  }, [images.length]);
  
  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.5, 4));
  };
  
  const handleZoomOut = () => {
    setZoom((prev) => {
      const newZoom = Math.max(prev - 0.5, 1);
      if (newZoom === 1) setPan({ x: 0, y: 0 });
      return newZoom;
    });
  };
  
  const resetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  
  // Mouse wheel zoom
  const handleWheel = (e) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      setZoom((prev) => Math.min(prev + 0.2, 4));
    } else {
      setZoom((prev) => {
        const newZoom = Math.max(prev - 0.2, 1);
        if (newZoom === 1) setPan({ x: 0, y: 0 });
        return newZoom;
      });
    }
  };
  
  // Pan when zoomed
  const handleMouseDown = (e) => {
    if (zoom > 1) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };
  
  const handleMouseMove = (e) => {
    if (isDragging && zoom > 1) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  };
  
  const handleMouseUp = () => {
    setIsDragging(false);
  };
  
  // Download image
  const handleDownload = async () => {
    const image = images[currentIndex];
    if (!image?.src) return;
    
    try {
      const response = await fetch(image.src);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = image.alt || `image-${currentIndex + 1}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      // Fallback: open in new tab
      window.open(image.src, '_blank');
    }
  };
  
  if (!images.length) return null;
  
  return (
    <>
      {/* Thumbnail Grid */}
      <div className="flex flex-wrap gap-1.5">
        {visibleImages.map((img, index) => (
          <button
            key={index}
            onClick={() => openLightbox(index)}
            className="relative w-20 h-20 rounded-md overflow-hidden bg-secondary/30 border border-border/30 hover:border-primary/50 transition-colors group"
          >
            <img
              src={img.src}
              alt={img.alt || `Image ${index + 1}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
          </button>
        ))}
        
        {/* "+N more" badge */}
        {hiddenCount > 0 && (
          <button
            onClick={() => openLightbox(MAX_VISIBLE)}
            className="relative w-20 h-20 rounded-md overflow-hidden bg-secondary/50 border border-border/30 hover:border-primary/50 transition-colors flex items-center justify-center"
          >
            {images[MAX_VISIBLE] && (
              <img
                src={images[MAX_VISIBLE].src}
                alt=""
                className="absolute inset-0 w-full h-full object-cover opacity-40"
              />
            )}
            <div className="absolute inset-0 bg-black/50" />
            <span className="relative text-white font-medium text-sm">+{hiddenCount}</span>
          </button>
        )}
      </div>
      
      {/* Lightbox Overlay */}
      {lightboxOpen && (
        <div 
          className="fixed inset-0 z-[100] bg-black/95 flex flex-col"
          onClick={() => setLightboxOpen(false)}
        >
          {/* Top Bar */}
          <div 
            className="flex items-center justify-between px-4 py-3 bg-black/50"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-white/80 text-sm">
              {currentIndex + 1} / {images.length}
            </div>
            
            <div className="flex items-center gap-1">
              {/* Zoom controls */}
              <button
                onClick={handleZoomOut}
                disabled={zoom <= 1}
                className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Zoom out (-)"
              >
                <ZoomOut size={18} />
              </button>
              <span className="text-white/60 text-xs w-12 text-center">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                disabled={zoom >= 4}
                className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                title="Zoom in (+)"
              >
                <ZoomIn size={18} />
              </button>
              {zoom > 1 && (
                <button
                  onClick={resetZoom}
                  className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                  title="Reset zoom (0)"
                >
                  <RotateCcw size={18} />
                </button>
              )}
              
              <div className="w-px h-5 bg-white/20 mx-2" />
              
              {/* Download */}
              <button
                onClick={handleDownload}
                className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                title="Download"
              >
                <Download size={18} />
              </button>
              
              {/* Close */}
              <button
                onClick={() => setLightboxOpen(false)}
                className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors ml-2"
                title="Close (ESC)"
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          {/* Main Image Area */}
          <div 
            ref={containerRef}
            className="flex-1 flex items-center justify-center relative overflow-hidden"
            onClick={(e) => e.stopPropagation()}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{ cursor: zoom > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
          >
            {/* Previous Arrow */}
            <button
              onClick={(e) => { e.stopPropagation(); goToPrevious(); }}
              className="absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/50 text-white/80 hover:text-white hover:bg-black/70 transition-colors z-10"
              title="Previous (←)"
            >
              <ChevronLeft size={24} />
            </button>
            
            {/* Image */}
            <img
              ref={imageRef}
              src={images[currentIndex]?.src}
              alt={images[currentIndex]?.alt || `Image ${currentIndex + 1}`}
              className="max-w-full max-h-full object-contain select-none transition-transform duration-100"
              style={{
                transform: `scale(${zoom}) translate(${pan.x / zoom}px, ${pan.y / zoom}px)`,
              }}
              draggable={false}
              onError={(e) => {
                e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="%23333" width="200" height="200"/><text fill="%23999" x="50%" y="50%" text-anchor="middle" dy=".3em">Failed to load</text></svg>';
              }}
            />
            
            {/* Next Arrow */}
            <button
              onClick={(e) => { e.stopPropagation(); goToNext(); }}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/50 text-white/80 hover:text-white hover:bg-black/70 transition-colors z-10"
              title="Next (→)"
            >
              <ChevronRight size={24} />
            </button>
          </div>
          
          {/* Thumbnail Strip */}
          <div 
            className="px-4 py-3 bg-black/50"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-center gap-1.5 overflow-x-auto max-w-full">
              {images.map((img, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentIndex(index)}
                  className={`relative w-12 h-12 rounded overflow-hidden shrink-0 transition-all ${
                    index === currentIndex 
                      ? 'ring-2 ring-white ring-offset-2 ring-offset-black' 
                      : 'opacity-50 hover:opacity-80'
                  }`}
                >
                  <img
                    src={img.src}
                    alt={img.alt || `Thumbnail ${index + 1}`}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.style.background = '#333';
                    }}
                  />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ImageGallery;
