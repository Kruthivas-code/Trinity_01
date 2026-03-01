/**
 * ArticleSidebar — Left sidebar with article navigation tree
 */
import { useState } from 'react';
import {
  ChevronDown, ChevronRight, Plus, Settings,
  FolderOpen, FileText, Trash2, Loader2, ThumbsUp
} from 'lucide-react';

const NavGroup = ({ group, groupKey, articles, selectedSlug, onSelect, expanded, setExpanded, onDelete, deleting, theme }) => {
  const isExpanded = expanded[groupKey] !== false;
  return (
    <div>
      <button onClick={() => setExpanded(prev => ({ ...prev, [groupKey]: !prev[groupKey] }))}
        className={`w-full flex items-center gap-2 px-2 py-1.5 ${theme.textMuted} ${theme.hoverText} transition-colors`}>
        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <FolderOpen className={`w-3.5 h-3.5 ${theme.textSecondary}`} />
        <span className="text-xs font-medium truncate">{group.group || group.label}</span>
        <span className={`text-[10px] ${theme.textTertiary} ml-auto`}>{articles.length}</span>
      </button>
      {isExpanded && (
        <div className="ml-5 space-y-0.5">
          {articles.map(art => {
            const isActive = art.slug === selectedSlug;
            const fbPct = art.feedback_total > 0 ? Math.round((art.feedback_helpful / art.feedback_total) * 100) : null;
            return (
              <div key={art.slug} className={`group flex items-center gap-1 rounded-lg transition-colors ${isActive ? theme.activeItem : `${theme.textMuted} ${theme.hover} ${theme.hoverText}`}`}>
                <button onClick={() => onSelect(art.slug)} className="flex-1 flex items-center gap-2 px-2 py-1.5 text-left min-w-0" data-testid={`nav-article-${art.slug}`}>
                  <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="text-sm truncate">{art.title}</span>
                </button>
                {fbPct !== null && (
                  <span className={`text-[9px] px-1 py-0.5 rounded flex items-center gap-0.5 flex-shrink-0 ${fbPct >= 70 ? 'bg-emerald-500/15 text-emerald-400' : fbPct >= 40 ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'}`} title={`${art.feedback_helpful}/${art.feedback_total} found helpful`}>
                    <ThumbsUp className="w-2.5 h-2.5" />{fbPct}%
                  </span>
                )}
                {!art.published && <span className="text-[9px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-400">draft</span>}
                <button onClick={() => onDelete(art.slug)} disabled={deleting === art.slug}
                  className={`p-1 opacity-0 group-hover:opacity-100 ${theme.textSecondary} hover:text-red-400 rounded transition-all flex-shrink-0`}>
                  {deleting === art.slug ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const ArticleSidebar = ({ tree, selectedSlug, onSelect, onDelete, deleting, expanded, setExpanded, onNewArticle, theme }) => (
  <aside className={`w-64 flex-shrink-0 border-r ${theme.border} ${theme.panelBg} flex flex-col overflow-hidden`} style={theme.panelBgStyle} data-testid="editor-sidebar">
    <div className={`px-3 py-3 flex items-center justify-between border-b ${theme.border}`}>
      <span className={`text-xs font-semibold ${theme.textSecondary} uppercase tracking-wider`}>Articles</span>
      <button onClick={onNewArticle} className={`p-1 ${theme.textSecondary} hover:text-[#00A1B2] rounded transition-colors`} title="New article" data-testid="new-article-btn">
        <Plus className="w-4 h-4" />
      </button>
    </div>
    <div className="flex-1 overflow-y-auto scrollbar-on-hover px-2 py-2">
      {tree.map(group => (
        <div key={group.key} className="mb-3">
          <div className="px-2 py-1 text-[10px] font-semibold text-[#00A1B2]/70 uppercase tracking-wider">{group.label}</div>
          {group.sections.map(sec => (
            <NavGroup key={sec.key} group={sec} groupKey={`${group.key}-${sec.key}`} articles={sec.articles} selectedSlug={selectedSlug} onSelect={onSelect} expanded={expanded} setExpanded={setExpanded} onDelete={onDelete} deleting={deleting} theme={theme} />
          ))}
        </div>
      ))}
    </div>
  </aside>
);
