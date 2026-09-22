/**
 * ImagePickerModal — Image Picker upgrade (Phase 4 of the help-doc-v3 port).
 * Three tabs: Stock (Unsplash search, proxied through the backend), GIF
 * (Giphy, called directly client-side — same as help-doc-v3, no backend
 * proxy needed since Giphy's public demo key is meant for client use), and
 * Upload (reuses Trinity's existing POST /api/kb/admin/images flow via the
 * `onUploadImage` prop KBEditor already passes into RichTextEditor — no
 * separate upload path).
 *
 * Ported from help-doc-v3's frontend/src/components/editor/ImagePickerModal.jsx,
 * restyled to Trinity's kb-editor `theme` prop convention (editorTheme.js)
 * instead of that file's zinc/dark: Tailwind classes, and its insert output
 * changed to match Trinity's REAL component vocabulary (routes/assistant.py's
 * COMPONENT_GUIDE / frontend/src/lib/mdx/parser.js): a captioned image is
 * `<Figure src="..." alt="..." caption="..." />`, not a `cols`-less
 * Mintlify-style tag — help-doc-v3 already happened to use `<Figure>` for
 * its Stock tab, which is also Trinity's real self-closing media tag, so
 * that output carries over unchanged; the GIF tab's plain `![alt](url)` is
 * ordinary Markdown either way.
 *
 * Alt-text-or-decorative gate before insert is preserved exactly (ported
 * behavior, not a Trinity-specific decision): insert is disabled until the
 * user either types alt text or checks "this image is decorative".
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, Search, Upload, Image as ImageIcon, Loader2, Check,
  ChevronLeft, ChevronRight, Sparkles,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Giphy's public "beta" demo key — meant for exactly this kind of
// client-side, low-volume, rate-limited use. Matches help-doc-v3's
// GifSearch component byte-for-byte (same key, same endpoints, called
// directly from the browser — no backend proxy).
const GIPHY_DEMO_KEY = 'dc6zaTOxFJmzC';

const TabButton = ({ active, onClick, children, icon: Icon, theme }) => (
  <button
    type="button"
    onClick={onClick}
    className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
      active ? 'bg-[#00A1B2] text-white' : `${theme.textMuted} ${theme.hoverText} ${theme.hover}`
    }`}
    data-testid={`image-picker-tab-${(children || '').toString().toLowerCase().replace(/\s+/g, '-')}`}
  >
    {Icon && <Icon className="w-3.5 h-3.5" />}
    {children}
  </button>
);

const ImageCard = ({ image, selected, onSelect, theme }) => (
  <button
    type="button"
    onClick={() => onSelect(image)}
    className={`relative group rounded-lg overflow-hidden border-2 transition-all ${
      selected ? 'border-[#00A1B2] ring-2 ring-[#00A1B2]/30' : `border-transparent hover:${theme.borderSubtle}`
    }`}
    data-testid={`image-card-${image.id}`}
  >
    <img src={image.thumb || image.small || image.url} alt={image.alt} className="w-full h-28 object-cover" loading="lazy" />
    {selected && (
      <div className="absolute inset-0 bg-[#00A1B2]/20 flex items-center justify-center">
        <div className="bg-[#00A1B2] rounded-full p-1"><Check className="w-4 h-4 text-white" /></div>
      </div>
    )}
    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
      <p className="text-xs text-white truncate">{image.alt}</p>
      {image.author && <p className="text-[10px] text-slate-300 truncate">by {image.author}</p>}
    </div>
  </button>
);

const GifSearch = ({ onSelect, selectedImage, theme }) => {
  const [query, setQuery] = useState('');
  const [gifs, setGifs] = useState([]);
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchTrending = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`https://api.giphy.com/v1/gifs/trending?api_key=${GIPHY_DEMO_KEY}&limit=12&rating=g`);
      const data = await res.json();
      setTrending((data.data || []).map((gif) => ({
        id: gif.id, url: gif.images.original.url,
        thumb: gif.images.fixed_width_small.url, small: gif.images.fixed_width.url,
        alt: gif.title, source: 'giphy',
      })));
    } catch (e) { console.error('Failed to fetch trending GIFs:', e); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchTrending(); }, [fetchTrending]);

  const searchGifs = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`https://api.giphy.com/v1/gifs/search?api_key=${GIPHY_DEMO_KEY}&q=${encodeURIComponent(query)}&limit=12&rating=g`);
      const data = await res.json();
      setGifs((data.data || []).map((gif) => ({
        id: gif.id, url: gif.images.original.url,
        thumb: gif.images.fixed_width_small.url, small: gif.images.fixed_width.url,
        alt: gif.title, source: 'giphy',
      })));
    } catch (e) { console.error('Failed to search GIFs:', e); }
    setLoading(false);
  };

  const displayGifs = query.trim() ? gifs : trending;

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchGifs()}
            placeholder="Search GIFs…"
            className={`w-full pl-8 pr-3 py-2 text-sm rounded-lg border ${theme.inputBg} ${theme.inputBorder} ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none`}
            style={theme.inputBgStyle}
            data-testid="gif-search-input"
          />
        </div>
        <button type="button" onClick={searchGifs} className="px-3 py-2 bg-[#00A1B2] hover:opacity-90 text-white text-sm font-medium rounded-lg transition-opacity" data-testid="gif-search-btn">
          Search
        </button>
      </div>
      {loading ? (
        <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-[#00A1B2] animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-3 gap-2 max-h-[340px] overflow-y-auto">
          {displayGifs.map((gif) => <ImageCard key={gif.id} image={gif} selected={selectedImage?.id === gif.id} onSelect={onSelect} theme={theme} />)}
        </div>
      )}
      {!loading && displayGifs.length === 0 && query && (
        <p className={`text-center text-sm py-6 ${theme.textMuted}`}>No GIFs found for &quot;{query}&quot;</p>
      )}
      <p className={`text-[10px] text-center ${theme.textSecondary}`}>Powered by GIPHY</p>
    </div>
  );
};

const StockImageSearch = ({ onSelect, selectedImage, theme }) => {
  const [query, setQuery] = useState('');
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [error, setError] = useState(null);
  const suggestions = ['technology', 'nature', 'business', 'abstract', 'minimal', 'code'];

  const searchImages = async (searchQuery, pageNum = 1) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API}/api/kb/admin/images/search-stock?query=${encodeURIComponent(searchQuery)}&page=${pageNum}&per_page=12`,
        { credentials: 'include' },
      );
      const data = await res.json();
      setImages(data.images || []);
      setTotalPages(data.total_pages || 0);
      setPage(pageNum);
      if (data.error) setError(data.error);
    } catch (e) {
      console.error('Failed to search images:', e);
      setError('Stock image search failed.');
    }
    setLoading(false);
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchImages(query, 1)}
            placeholder="Search stock images…"
            className={`w-full pl-8 pr-3 py-2 text-sm rounded-lg border ${theme.inputBg} ${theme.inputBorder} ${theme.inputText} ${theme.placeholder} focus:border-[#00A1B2] focus:outline-none`}
            style={theme.inputBgStyle}
            data-testid="stock-search-input"
          />
        </div>
        <button type="button" onClick={() => searchImages(query, 1)} className="px-3 py-2 bg-[#00A1B2] hover:opacity-90 text-white text-sm font-medium rounded-lg transition-opacity" data-testid="stock-search-btn">
          Search
        </button>
      </div>

      {images.length === 0 && !loading && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => { setQuery(s); searchImages(s, 1); }}
              className={`px-2.5 py-1 text-xs rounded-full transition-colors ${theme.inputBg} ${theme.textMuted} ${theme.hoverText} border ${theme.inputBorder}`}>
              {s}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-[#00A1B2] animate-spin" /></div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-2 max-h-[300px] overflow-y-auto">
            {images.map((image) => <ImageCard key={image.id} image={image} selected={selectedImage?.id === image.id} onSelect={onSelect} theme={theme} />)}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button type="button" onClick={() => searchImages(query, page - 1)} disabled={page <= 1}
                className={`p-1.5 rounded-lg disabled:opacity-40 ${theme.inputBg} ${theme.hover}`}>
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className={`text-xs ${theme.textMuted}`}>Page {page} of {totalPages}</span>
              <button type="button" onClick={() => searchImages(query, page + 1)} disabled={page >= totalPages}
                className={`p-1.5 rounded-lg disabled:opacity-40 ${theme.inputBg} ${theme.hover}`}>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
      {!loading && images.length === 0 && query && !error && (
        <p className={`text-center text-sm py-6 ${theme.textMuted}`}>No images found for &quot;{query}&quot;</p>
      )}
      {error && <p className="text-center text-xs text-rose-500">{error}</p>}
    </div>
  );
};

const UploadTab = ({ onSelect, selectedImage, onUploadImage, theme }) => {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !file.type.startsWith('image/')) return;
    setUploading(true);
    try {
      // Reuses Trinity's existing upload path — the same onUploadImage
      // callback KBEditor already wires into RichTextEditor's toolbar
      // upload button (POST /api/kb/admin/images), not a second endpoint.
      const url = await onUploadImage(file);
      if (url) {
        onSelect({
          id: `upload-${Date.now()}`, url, thumb: url, small: url,
          alt: file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '),
          source: 'upload',
        });
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors hover:border-[#00A1B2] ${theme.inputBorder}`}
        data-testid="upload-dropzone"
      >
        {uploading ? <Loader2 className="w-8 h-8 text-[#00A1B2] animate-spin mx-auto mb-2" /> : <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />}
        <p className={`text-sm font-medium ${theme.text}`}>{uploading ? 'Uploading…' : 'Click to upload'}</p>
        <p className={`text-xs mt-1 ${theme.textSecondary}`}>PNG, JPG, GIF, WebP, SVG up to 10MB</p>
      </div>
      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
      {selectedImage?.source === 'upload' && (
        <div className="relative rounded-lg overflow-hidden border-2 border-[#00A1B2]">
          <img src={selectedImage.url} alt={selectedImage.alt} className="w-full h-40 object-cover" />
          <div className="absolute top-2 right-2 bg-[#00A1B2] rounded-full p-1"><Check className="w-4 h-4 text-white" /></div>
        </div>
      )}
    </div>
  );
};

export const ImagePickerModal = ({ isOpen, onClose, onInsert, onUploadImage, theme, initialTab = 'stock' }) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [selectedImage, setSelectedImage] = useState(null);
  const [altText, setAltText] = useState('');
  const [decorative, setDecorative] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      setSelectedImage(null);
      setAltText('');
      setDecorative(false);
    }
  }, [isOpen, initialTab]);

  useEffect(() => {
    setAltText(selectedImage?.alt || '');
    setDecorative(false);
  }, [selectedImage]);

  const altReady = decorative || altText.trim().length > 0;

  const handleInsert = () => {
    if (!selectedImage || !altReady) return;
    const alt = decorative ? '' : altText.trim();
    // GIF: plain markdown image (help-doc-v3 parity). Everything else
    // (stock + upload): Trinity's real <Figure> media component — see the
    // module header comment for why this differs from a bare ![]().
    const markdown = activeTab === 'gif'
      ? `![${alt}](${selectedImage.url})`
      : `<Figure src="${selectedImage.url}" alt="${alt}" caption="${alt}" />`;
    onInsert(markdown);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 backdrop-blur-sm" data-testid="image-picker-modal">
      <div className={`${theme.panelBg} border ${theme.border} rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] overflow-hidden flex flex-col`} style={theme.panelBgStyle}>
        <div className={`flex items-center justify-between px-5 py-3.5 border-b ${theme.border} flex-shrink-0`}>
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-[#00A1B2]/10 rounded-lg"><ImageIcon className="w-4 h-4 text-[#00A1B2]" /></div>
            <div>
              <h2 className={`text-sm font-semibold ${theme.text}`}>Insert Image</h2>
              <p className={`text-xs ${theme.textSecondary}`}>Search stock images, GIFs, or upload your own</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className={`p-1.5 rounded-md transition-colors ${theme.textMuted} ${theme.hoverText} ${theme.hover}`} data-testid="image-picker-close">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className={`flex gap-1 px-5 py-2.5 border-b ${theme.border} flex-shrink-0`}>
          <TabButton active={activeTab === 'stock'} onClick={() => setActiveTab('stock')} icon={Sparkles} theme={theme}>Stock</TabButton>
          <TabButton active={activeTab === 'gif'} onClick={() => setActiveTab('gif')} icon={ImageIcon} theme={theme}>GIF</TabButton>
          <TabButton active={activeTab === 'upload'} onClick={() => setActiveTab('upload')} icon={Upload} theme={theme}>Upload</TabButton>
        </div>

        <div className="p-5 overflow-y-auto flex-1">
          {activeTab === 'stock' && <StockImageSearch onSelect={setSelectedImage} selectedImage={selectedImage} theme={theme} />}
          {activeTab === 'gif' && <GifSearch onSelect={setSelectedImage} selectedImage={selectedImage} theme={theme} />}
          {activeTab === 'upload' && <UploadTab onSelect={setSelectedImage} selectedImage={selectedImage} onUploadImage={onUploadImage} theme={theme} />}
        </div>

        {selectedImage && (
          <div className={`px-5 py-3 border-t ${theme.border} flex-shrink-0`} data-testid="alt-text-row">
            <label className={`block text-xs font-medium mb-1 ${theme.textMuted}`}>
              Alt text {decorative ? '(disabled — decorative)' : <span className="text-rose-500">*</span>}
            </label>
            <input
              value={altText}
              onChange={(e) => setAltText(e.target.value)}
              disabled={decorative}
              placeholder="Describe the image for screen readers and SEO"
              className={`w-full text-sm rounded-md border px-3 py-2 outline-none focus:border-[#00A1B2] disabled:opacity-50 ${theme.inputBg} ${theme.inputBorder} ${theme.inputText}`}
              style={theme.inputBgStyle}
              data-testid="alt-text-input"
            />
            <label className={`mt-2 flex items-center gap-2 text-xs cursor-pointer ${theme.textMuted}`}>
              <input type="checkbox" checked={decorative} onChange={(e) => setDecorative(e.target.checked)} data-testid="alt-decorative-checkbox" />
              This image is decorative (empty alt)
            </label>
          </div>
        )}

        <div className={`flex items-center justify-between px-5 py-3.5 border-t ${theme.border} flex-shrink-0`}>
          <div className={`text-xs ${theme.textMuted}`}>
            {selectedImage ? (
              !altReady
                ? <span className="text-rose-500">Add alt text or mark the image decorative</span>
                : <span className="flex items-center gap-1.5 text-[#00A1B2]"><Check className="w-3.5 h-3.5" /> Image selected</span>
            ) : 'Select an image to insert'}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className={`px-3 py-1.5 text-sm font-medium transition-colors ${theme.textMuted} ${theme.hoverText}`}>
              Cancel
            </button>
            <button
              type="button"
              onClick={handleInsert}
              disabled={!selectedImage || !altReady}
              className="px-4 py-1.5 bg-[#00A1B2] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-md transition-opacity"
              data-testid="image-insert-confirm"
            >
              Insert Image
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImagePickerModal;
