/**
 * ArticlePreview — Full-page preview of KB article content
 * Renders content identically to PublicDocs using DocContent
 * Supports desktop, tablet, and mobile viewport previews
 */
import { useState } from 'react';
import { ArrowLeft, Monitor, Tablet, Smartphone } from 'lucide-react';
import { DocContent } from '../../components/docs/DocContent';

const VIEWPORTS = [
  { key: 'desktop', label: 'Desktop', icon: Monitor, width: '100%' },
  { key: 'tablet', label: 'Tablet', icon: Tablet, width: '768px' },
  { key: 'mobile', label: 'Mobile', icon: Smartphone, width: '375px' },
];

export const ArticlePreview = ({ form, theme, isDark, onBack }) => {
  const [viewport, setViewport] = useState('desktop');
  const activeVP = VIEWPORTS.find(v => v.key === viewport);

  return (
    <div className={`fixed inset-0 z-50 flex flex-col ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`} data-testid="article-preview">
      {/* Preview Header */}
      <header
        className={`h-14 flex items-center px-4 border-b flex-shrink-0 gap-3 ${isDark ? 'bg-[#0c0c0c] border-slate-800/80' : 'bg-white border-gray-200'}`}
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
        <div className={`w-px h-6 ${isDark ? 'bg-slate-700/40' : 'bg-gray-200'}`} />
        <span className={`text-sm truncate ${isDark ? 'text-white' : 'text-gray-900'}`}>
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
      <div className={`flex-1 overflow-y-auto flex justify-center ${viewport !== 'desktop' ? 'py-8 px-4' : ''}`}>
        <div
          className="transition-all duration-300 ease-in-out h-full"
          style={{
            width: activeVP.width,
            maxWidth: '100%',
            ...(viewport !== 'desktop' ? {
              boxShadow: isDark
                ? '0 0 0 1px rgba(255,255,255,0.1), 0 8px 32px rgba(0,0,0,0.4)'
                : '0 0 0 1px rgba(0,0,0,0.08), 0 8px 32px rgba(0,0,0,0.1)',
              borderRadius: '12px',
              overflow: 'hidden',
            } : {})
          }}
          data-testid="preview-viewport-container"
        >
          <div
            className={`h-full overflow-y-auto ${isDark ? 'bg-[#0a0a0a]' : 'bg-white'}`}
          >
            <article className="max-w-[800px] mx-auto px-6 py-8 animate-fadeIn">
              {form?.title && (
                <h1
                  className={`font-bold mb-8 ${isDark ? 'text-white' : 'text-gray-900'}`}
                  style={{ fontFamily: "'Brockmann', sans-serif", fontSize: '30px', lineHeight: '36px', letterSpacing: '-0.01em' }}
                >
                  {form.title}
                </h1>
              )}
              <div
                className={`docs-prose prose ${isDark ? 'prose-invert prose-p:text-[#999999] prose-li:text-[#999999] prose-strong:text-white prose-pre:bg-slate-900 prose-pre:border prose-pre:border-white/10' : 'prose-gray prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200'} max-w-none overflow-hidden prose-headings:font-semibold prose-headings:text-inherit prose-h2:text-xl sm:prose-h2:text-2xl prose-h2:mt-10 prose-h2:mb-4 prose-h3:text-lg sm:prose-h3:text-xl prose-h3:mt-8 prose-h3:mb-3 prose-p:text-[15px] sm:prose-p:text-base prose-p:leading-7 prose-p:break-words prose-a:text-[#00A1B2] prose-a:no-underline hover:prose-a:underline prose-code:text-[#00A1B2] prose-code:bg-[#00A1B2]/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:break-words prose-code:text-[13px] sm:prose-code:text-sm prose-pre:rounded-xl prose-pre:overflow-x-auto prose-pre:text-[13px] sm:prose-pre:text-sm prose-img:rounded-lg prose-img:max-w-full prose-img:h-auto`}
                data-testid="preview-article-body"
              >
                <DocContent
                  content={
                    form?.content_markdown
                      ? form.content_markdown.replace(
                          new RegExp(`^#\\s*${(form?.title || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n+`, 'i'),
                          ''
                        )
                      : ''
                  }
                  onHeadings={() => {}}
                />
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  );
};
