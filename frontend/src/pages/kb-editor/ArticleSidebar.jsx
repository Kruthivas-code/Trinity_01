/**
 * ArticleSidebar — Left sidebar with the (read/browse) navigation tree.
 * - Recursive: a group can nest further groups to any depth, each with its
 *   own expand/collapse state.
 * - Hover on a group shows "+" (new page in that exact group).
 * - Hover on a page shows its settings gear (via CSS group-hover).
 * - Structural edits (rename/delete/reorder/move/visibility) live in
 *   Settings > Navigation (NavManager) — this sidebar is for browsing and
 *   quickly adding a page to a specific group, not for restructuring.
 */
import {
  ChevronDown, ChevronRight, Plus, Settings, FolderOpen
} from 'lucide-react';

/* ---------- Single article item ---------- */
const ArticleItem = ({ article, depth, selectedSlug, onSelect, onOpenSettings, theme }) => {
  const isActive = article.slug === selectedSlug;

  return (
    <div
      className={`group/art flex items-center gap-1 rounded-lg transition-colors ${isActive ? theme.activeItem : `${theme.textMuted} ${theme.hover} ${theme.hoverText}`}`}
      style={{ paddingLeft: `${depth * 0.9}rem` }}
    >
      <button
        onClick={() => onSelect(article.slug)}
        className="flex-1 flex items-center gap-2 px-2 py-1.5 text-left min-w-0"
        data-testid={`nav-article-${article.slug}`}
      >
        <span className="text-sm truncate">{article.sidebar_title || article.title}</span>
      </button>

      {/* Draft tag — visible when NOT hovered, hidden on hover (replaced by gear) */}
      {!article.published && (
        <span className="text-[9px] px-1.5 py-0.5 mr-1.5 rounded bg-slate-500/20 text-slate-400 flex-shrink-0 group-hover/art:hidden" data-testid={`draft-tag-${article.slug}`}>
          draft
        </span>
      )}

      {/* Settings gear — hidden by default, visible on hover */}
      <button
        onClick={(e) => { e.stopPropagation(); onOpenSettings(article); }}
        className={`p-1 mr-1 rounded transition-all flex-shrink-0 hidden group-hover/art:block ${theme.textSecondary} hover:text-[#00A1B2]`}
        title="Page settings"
        data-testid={`settings-btn-${article.slug}`}
      >
        <Settings className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

/* ---------- One tree node, rendered recursively (group or page) ---------- */
const NavTreeNode = ({ node, topGroupKey, depth, selectedSlug, onSelect, onOpenSettings, onCreatePage, expanded, setExpanded, theme, isOwner }) => {
  if (node.type === 'page') {
    // A page whose article couldn't be resolved (e.g. deleted out from under
    // the tree) is simply skipped here — structural cleanup is NavManager's job.
    if (!node.article) return null;
    return (
      <ArticleItem article={node.article} depth={depth} selectedSlug={selectedSlug} onSelect={onSelect} onOpenSettings={onOpenSettings} theme={theme} />
    );
  }

  const expKey = `${topGroupKey}::${node.key}`;
  const isExpanded = expanded[expKey] !== false;
  const isHidden = node.published === false;
  const isTop = depth === 0;
  const children = node.children || [];

  return (
    <div className={isTop ? 'mb-3' : 'mb-0.5'}>
      <div
        className={`group/grp flex items-center gap-1 rounded-md transition-colors ${theme.hover}`}
        style={{ paddingLeft: `${depth * 0.9}rem` }}
      >
        <button
          onClick={() => setExpanded(prev => ({ ...prev, [expKey]: !prev[expKey] }))}
          className={`p-0.5 rounded transition-colors ${theme.textSecondary} ${theme.hoverText}`}
          data-testid={`toggle-group-${node.key}`}
        >
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>
        {!isTop && <FolderOpen className={`w-3.5 h-3.5 ${theme.textSecondary} flex-shrink-0`} />}
        <span className={`flex-1 truncate ${isHidden ? 'opacity-50' : ''} ${isTop ? `text-[11px] font-semibold uppercase tracking-wider ${theme.id === 'dark' ? 'text-[#00A1B2]/70' : 'text-[#00A1B2]'}` : `text-xs font-medium ${theme.textMuted}`}`}>
          {node.label}
        </span>

        {isHidden && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-500/20 text-slate-400 flex-shrink-0 group-hover/grp:hidden" data-testid={`hidden-tag-group-${node.key}`}>
            hidden
          </span>
        )}

        {/* Creating a page is owner-only (Phase 1) — hide the control
            rather than let a non-owner hit a 403 on click. */}
        {isOwner && (
          <div className="flex items-center gap-0.5 opacity-0 group-hover/grp:opacity-100 transition-all">
            <button
              onClick={(e) => { e.stopPropagation(); onCreatePage(topGroupKey, node); }}
              className={`p-0.5 rounded transition-colors ${theme.textSecondary} hover:text-[#00A1B2]`}
              title={`New page in ${node.label}`}
              data-testid={`add-page-in-group-${node.key}`}
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {isExpanded && children.length > 0 && (
        <div className={isTop ? 'mt-0.5' : ''}>
          {children.map((child, i) => (
            <NavTreeNode
              key={i}
              node={child}
              topGroupKey={topGroupKey}
              depth={depth + 1}
              selectedSlug={selectedSlug}
              onSelect={onSelect}
              onOpenSettings={onOpenSettings}
              onCreatePage={onCreatePage}
              expanded={expanded}
              setExpanded={setExpanded}
              theme={theme}
              isOwner={isOwner}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/* ---------- Main sidebar export ---------- */
export const ArticleSidebar = ({
  tree,
  selectedSlug,
  onSelect,
  expanded,
  setExpanded,
  onNewCategory,
  onOpenSettings,
  onCreatePage,
  theme,
  isOwner
}) => (
  <aside
    className={`w-64 flex-shrink-0 border-r ${theme.border} ${theme.panelBg} flex flex-col overflow-hidden relative z-30`}
    style={theme.panelBgStyle}
    data-testid="editor-sidebar"
  >
    <div className={`px-3 py-3 flex items-center justify-between border-b ${theme.border}`}>
      <span className={`text-xs font-semibold ${theme.textSecondary} uppercase tracking-wider`}>Navigation</span>
      {/* Adding a top-level category means editing the nav tree — owner-only (Phase 1). */}
      {isOwner && (
        <button
          onClick={onNewCategory}
          className={`p-1 ${theme.textSecondary} hover:text-[#00A1B2] rounded transition-colors`}
          title="New category"
          data-testid="new-category-btn"
        >
          <Plus className="w-4 h-4" />
        </button>
      )}
    </div>
    <div className="flex-1 overflow-y-auto scrollbar-on-hover px-2 py-2">
      {tree.map(group => (
        <NavTreeNode
          key={group.key}
          node={group}
          topGroupKey={group.key}
          depth={0}
          selectedSlug={selectedSlug}
          onSelect={onSelect}
          onOpenSettings={onOpenSettings}
          onCreatePage={onCreatePage}
          expanded={expanded}
          setExpanded={setExpanded}
          theme={theme}
          isOwner={isOwner}
        />
      ))}
    </div>
  </aside>
);
