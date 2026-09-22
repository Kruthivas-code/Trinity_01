/**
 * Media - Phase 5 of the help-doc-v3 feature port.
 * Ported from help-doc-v3's frontend/src/components/docs/Media.jsx, adapted
 * to Trinity's own image URL scheme and component set:
 *  - DocImage: responsive (srcset via the backend's `?w=&format=webp`
 *    resize-on-read added to GET /api/kb/images/{filename}), click-to-zoom
 *    lightbox, lazy/async loading. Used for both `<Figure>` and plain
 *    markdown images (DocContent.jsx).
 *  - YouTubeEmbed / LoomEmbed: click-to-load -- a lightweight thumbnail +
 *    play button that only mounts the real iframe once clicked, so an
 *    unwatched video embed costs nothing on page load. Reuses the same
 *    id-parsing DocContent.jsx already had for `<YouTube id="..." />` /
 *    `<Loom id="..." />` (per COMPONENT_GUIDE).
 *
 * Trinity uploads images to Mongo (kb_image_files) and serves them back at
 * a root-relative `/api/kb/images/{filename}` URL (see routes/kb.py's
 * POST /admin/images -> {"url": f"/api/kb/images/{unique_name}"}) rather
 * than help-doc-v3's `/api/public/files/` -- only that prefix differs below.
 * Images picked from the Stock/GIF tabs of the image picker are absolute
 * third-party URLs (Unsplash/Giphy) and are served as-is, un-transformed.
 */
import { useState, useEffect, useRef } from 'react';
import { X, Play, ZoomIn } from 'lucide-react';

const SRCSET_WIDTHS = [480, 768, 1080, 1600];
const isTransformable = (src) => typeof src === 'string' && src.includes('/api/kb/images/');

const withParams = (src, params) => {
  try {
    const [base, q = ''] = src.split('?');
    const usp = new URLSearchParams(q);
    Object.entries(params).forEach(([k, v]) => usp.set(k, v));
    return `${base}?${usp.toString()}`;
  } catch {
    return src;
  }
};

const buildSrcSet = (src) =>
  SRCSET_WIDTHS.map((w) => `${withParams(src, { w, format: 'webp' })} ${w}w`).join(', ');

const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- Lightbox ---------- */
const Lightbox = ({ src, alt, onClose }) => {
  const closeRef = useRef(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={alt || 'Image preview'}
      data-testid="image-lightbox"
      onClick={onClose}
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4"
      style={prefersReducedMotion() ? {} : { animation: 'fadeIn .15s ease-out' }}
    >
      <button
        ref={closeRef}
        type="button"
        onClick={onClose}
        aria-label="Close image preview"
        data-testid="lightbox-close"
        className="absolute top-4 right-4 h-10 w-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center"
      >
        <X className="h-5 w-5" />
      </button>
      <figure className="max-w-[95vw] max-h-[90vh] flex flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
        <img
          src={isTransformable(src) ? withParams(src, { w: 1600, format: 'webp' }) : src}
          alt={alt || ''}
          className="max-w-full max-h-[82vh] object-contain rounded-lg"
        />
        {alt && alt.trim() && (
          <figcaption className="text-sm text-zinc-300 text-center max-w-2xl">{alt}</figcaption>
        )}
      </figure>
    </div>
  );
};

/* ---------- Responsive, zoomable image ---------- */
export const DocImage = ({ src, alt, caption, eager = false }) => {
  const [zoom, setZoom] = useState(false);
  if (!src) return null;
  const label = caption || alt;
  const transformable = isTransformable(src);

  const img = (
    <img
      src={transformable ? withParams(src, { w: 1080, format: 'webp' }) : src}
      {...(transformable ? { srcSet: buildSrcSet(src), sizes: '(max-width: 768px) 100vw, 768px' } : {})}
      alt={alt || ''}
      loading={eager ? 'eager' : 'lazy'}
      decoding="async"
      className="rounded-lg max-w-full h-auto"
      data-testid="doc-image"
    />
  );

  return (
    <>
      <figure className="my-6 relative z-10 group">
        <button
          type="button"
          onClick={() => setZoom(true)}
          aria-label={label ? `Zoom image: ${label}` : 'Zoom image'}
          className="block w-full cursor-zoom-in relative"
          data-testid="doc-image-zoom"
        >
          {img}
          <span className="absolute top-2 right-2 h-8 w-8 rounded-md bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <ZoomIn className="h-4 w-4" />
          </span>
        </button>
        {label && label.trim() && (
          <figcaption className="mt-2 text-sm text-gray-500 dark:text-[#999999] text-center">{label}</figcaption>
        )}
      </figure>
      {zoom && <Lightbox src={src} alt={label} onClose={() => setZoom(false)} />}
    </>
  );
};

/* ---------- Click-to-load video embeds ---------- */
const ThumbShell = ({ children, testId }) => (
  <div className="my-6 relative z-10" data-testid={testId}>{children}</div>
);

const PlayOverlay = () => (
  <span className="absolute inset-0 flex items-center justify-center">
    <span className="h-16 w-16 rounded-full bg-black/60 group-hover:bg-[#00A1B2] transition-colors flex items-center justify-center">
      <Play className="h-7 w-7 text-white translate-x-0.5" fill="currentColor" />
    </span>
  </span>
);

// Same id/URL parsing DocContent.jsx's inline YouTubeEmbed used before this
// port -- kept unchanged so `<YouTube id="..." />` (per COMPONENT_GUIDE)
// still resolves the same way, just now behind a click-to-load thumbnail.
const parseYouTubeId = (id) => {
  if (!id) return id;
  if (id.includes('youtube.com') || id.includes('youtu.be')) {
    const m = id.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    if (m) return m[1];
    const s = id.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
    if (s) return s[1].split('?')[0];
  }
  return id;
};

const parseLoomId = (id) => {
  if (!id) return id;
  if (id.includes('loom.com')) {
    const m = id.match(/loom\.com\/(?:share|embed)\/([a-zA-Z0-9]+)/);
    if (m) return m[1];
  }
  return id;
};

export const YouTubeEmbed = ({ id, title }) => {
  const [play, setPlay] = useState(false);
  if (!id) return null;
  const videoId = parseYouTubeId(id);
  return (
    <ThumbShell testId="youtube-embed">
      <div className="relative w-full rounded-xl overflow-hidden border border-gray-200 dark:border-slate-800 shadow-lg bg-gray-50 dark:bg-slate-900" style={{ paddingBottom: '56.25%' }}>
        {play ? (
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
            title={title || 'Video'}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlay(true)}
            aria-label={`Play video: ${title || 'YouTube video'}`}
            data-testid="youtube-play"
            className="group absolute inset-0 w-full h-full cursor-pointer"
          >
            <img
              src={`https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`}
              alt={title || 'Video thumbnail'}
              loading="lazy"
              decoding="async"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <PlayOverlay />
          </button>
        )}
      </div>
      {title && title.trim() && <p className="mt-2 text-sm text-gray-500 dark:text-[#999999] text-center">{title}</p>}
    </ThumbShell>
  );
};

export const LoomEmbed = ({ id, title }) => {
  const [play, setPlay] = useState(false);
  if (!id) return null;
  const loomId = parseLoomId(id);
  return (
    <ThumbShell testId="loom-embed">
      <div className="relative w-full rounded-xl overflow-hidden border border-gray-200 dark:border-slate-800 shadow-lg bg-gray-900" style={{ paddingBottom: '56.25%' }}>
        {play ? (
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.loom.com/embed/${loomId}?autoplay=1`}
            title={title || 'Video'}
            frameBorder="0"
            allowFullScreen
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlay(true)}
            aria-label={`Play video: ${title || 'Loom video'}`}
            data-testid="loom-play"
            className="group absolute inset-0 w-full h-full cursor-pointer bg-gradient-to-br from-[#625df5]/30 to-[#1588FC]/20"
          >
            <span className="absolute top-3 left-3 text-xs font-semibold text-white/80">Loom</span>
            <PlayOverlay />
          </button>
        )}
      </div>
      {title && title.trim() && <p className="mt-2 text-sm text-gray-500 dark:text-[#999999] text-center">{title}</p>}
    </ThumbShell>
  );
};
