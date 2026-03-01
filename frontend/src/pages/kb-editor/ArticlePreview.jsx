/**
 * ArticlePreview — Full-page preview that mirrors the actual Docs page
 * Uses an iframe to render /docs/:slug for 100% layout fidelity
 * Includes left sidebar, right TOC, main navbar, breadcrumb bar
 * Supports desktop, tablet, and mobile viewport switching
 */
import { useState } from 'react';
import { ArrowLeft, Monitor, Tablet, Smartphone, AlertCircle } from 'lucide-react';

const VIEWPORTS = [
  { key: 'desktop', label: 'Desktop', icon: Monitor, width: '100%' },
  { key: 'tablet', label: 'Tablet', icon: Tablet, width: '768px' },
  { key: 'mobile', label: 'Mobile', icon: Smartphone, width: '375px' },
];

export const ArticlePreview = ({ form, isDark, onBack }) => {
  const [viewport, setViewport] = useState('desktop');
  const activeVP = VIEWPORTS.find(v => v.key === viewport);

  const isPublished = form?.published && form?.slug;
  const previewUrl = isPublished ? `/docs/${form.slug}` : null;

  return (
    <div className={`fixed inset-0 z-50 flex flex-col ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-100'}`} data-testid="article-preview">
      {/* Preview Header */}
      <header
        className={`h-12 flex items-center px-4 border-b flex-shrink-0 gap-3 ${isDark ? 'bg-[#111] border-slate-800/80' : 'bg-white border-gray-200'}`}
        data-testid="preview-header"
      >
        <button
          onClick={onBack}
          className={`flex items-center gap-2 transition-colors ${isDark ? 'text-slate-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'}`}
          data-testid="preview-back-btn"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm font-medium">Back to Editor</span>
        </button>
        <div className={`w-px h-5 ${isDark ? 'bg-slate-700/40' : 'bg-gray-200'}`} />
        <span className={`text-sm truncate ${isDark ? 'text-slate-300' : 'text-gray-600'}`}>
          {form?.title || 'Untitled'}
        </span>

        <div className="flex items-center gap-1 ml-auto" data-testid="viewport-selector">
          {VIEWPORTS.map(vp => {
            const Icon = vp.icon;
            const isActive = viewport === vp.key;
            return (
              <button
                key={vp.key}
                onClick={() => setViewport(vp.key)}
                className={`p-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-[#00A1B2] text-white'
                    : isDark
                      ? 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                }`}
                title={vp.label}
                data-testid={`viewport-${vp.key}`}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
        </div>
      </header>

      {/* Preview Content */}
      <div className={`flex-1 overflow-hidden flex justify-center ${viewport !== 'desktop' ? 'py-6 px-4' : ''}`}>
        {isPublished ? (
          <div
            className="transition-all duration-300 ease-in-out h-full"
            style={{
              width: activeVP.width,
              maxWidth: '100%',
              ...(viewport !== 'desktop' ? {
                boxShadow: isDark
                  ? '0 0 0 1px rgba(255,255,255,0.08), 0 12px 40px rgba(0,0,0,0.5)'
                  : '0 0 0 1px rgba(0,0,0,0.06), 0 12px 40px rgba(0,0,0,0.12)',
                borderRadius: '12px',
                overflow: 'hidden',
              } : {})
            }}
            data-testid="preview-viewport-container"
          >
            <iframe
              src={previewUrl}
              className="w-full h-full border-none bg-white"
              title="Article Preview"
              data-testid="preview-iframe"
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full" data-testid="preview-unpublished-msg">
            <div className={`flex flex-col items-center gap-4 px-6 py-8 rounded-2xl max-w-md text-center ${isDark ? 'bg-slate-900/50 border border-slate-800' : 'bg-white border border-gray-200'}`}>
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isDark ? 'bg-amber-500/10' : 'bg-amber-50'}`}>
                <AlertCircle className="w-6 h-6 text-amber-500" />
              </div>
              <div>
                <h3 className={`text-base font-semibold mb-1.5 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Preview Unavailable
                </h3>
                <p className={`text-sm leading-relaxed ${isDark ? 'text-slate-400' : 'text-gray-500'}`}>
                  Save and publish this article to preview how it will appear on the public documentation site.
                </p>
              </div>
              <button
                onClick={onBack}
                className="px-4 py-2 bg-[#00A1B2] text-white text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
                data-testid="preview-go-back-btn"
              >
                Back to Editor
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
