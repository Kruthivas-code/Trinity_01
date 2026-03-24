/**
 * ArticleSidebar — Left sidebar with navigation tree
 * - Hover on category/subcategory shows "+" to create a page underneath
 * - Chevron click only toggles expand/collapse
 * - Hover on page shows settings gear icon (via CSS group-hover)
 * - Main "+" in header opens settings to create new tabs (categories)
 * - No page icons, no feedback metrics
 */
import {
  ChevronDown, ChevronRight, Plus, Settings, FolderOpen
} from 'lucide-react';

/* ---------- Section (subcategory) ---------- */
const NavSection = ({ section, groupKey, sectionKey, articles, selectedSlug, onSelect, expanded, setExpanded, onOpenSettings, onCreateInSection, theme }) => {
  const expKey = `${groupKey}-${sectionKey}`;
  const isExpanded = expanded[expKey] !== false;

  return (
    <div>
      <div className={`group/sec flex items-center gap-1 px-2 py-1.5 rounded-md transition-colors ${theme.textMuted} ${theme.hover}`}>
        {/* Chevron — only this toggles */}
        <button
          onClick={() => setExpanded(prev => ({ ...prev, [expKey]: !prev[expKey] }))}
          className={`p-0.5 rounded transition-colors ${theme.hoverText}`}
          data-testid={`toggle-section-${sectionKey}`}
        >
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        <FolderOpen className={`w-3.5 h-3.5 ${theme.textSecondary} flex-shrink-0`} />
        <span className="text-xs font-medium truncate flex-1">{section.label}</span>

        {/* "+" icon on hover to create page under this section */}
        <button
          onClick={(e) => { e.stopPropagation(); onCreateInSection(groupKey, section); }}
          className={`p-0.5 rounded transition-all opacity-0 group-hover/sec:opacity-100 ${theme.textSecondary} hover:text-[#00A1B2]`}
          title={`New page in ${section.label}`}
          data-testid={`add-page-in-section-${sectionKey}`}
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
      {isExpanded && (
        <div className="ml-5 space-y-0.5">
          {articles.map(art => (
            <ArticleItem
              key={art.slug}
              article={art}
              selectedSlug={selectedSlug}
              onSelect={onSelect}
              onOpenSettings={onOpenSettings}
              theme={theme}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/* ---------- Single article item ---------- */
const ArticleItem = ({ article, selectedSlug, onSelect, onOpenSettings, theme }) => {
  const isActive = article.slug === selectedSlug;

  return (
    <div
      className={`group/art flex items-center gap-1 rounded-lg transition-colors ${isActive ? theme.activeItem : `${theme.textMuted} ${theme.hover} ${theme.hoverText}`}`}
    >
      <button
        onClick={() => onSelect(article.slug)}
        className="flex-1 flex items-center gap-2 px-2 py-1.5 text-left min-w-0"
        data-testid={`nav-article-${article.slug}`}
      >
        <span className="text-sm truncate">{article.sidebar_title || article.title}</span>
      </button>

      {/* Draft tag — always visible for unpublished */}
      {!article.published && (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 flex-shrink-0" data-testid={`draft-tag-${article.slug}`}>
          draft
        </span>
      )}

      {/* Settings gear on hover (CSS-based) */}
      <button
        onClick={(e) => { e.stopPropagation(); onOpenSettings(article); }}
        className={`p-1 rounded transition-all flex-shrink-0 opacity-0 group-hover/art:opacity-100 ${theme.textSecondary} hover:text-[#00A1B2]`}
        title="Page settings"
        data-testid={`settings-btn-${article.slug}`}
      >
        <Settings className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};

/* ---------- Group (top-level category) ---------- */
const GroupItem = ({ group, selectedSlug, onSelect, expanded, setExpanded, onOpenSettings, onCreateInSection, onCreateInGroup, theme }) => {
  const expKey = `group-${group.key}`;
  const isExpanded = expanded[expKey] !== false;

  return (
    <div className="mb-3">
      <div className={`group/grp flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${theme.hover}`}>
        <button
          onClick={() => setExpanded(prev => ({ ...prev, [expKey]: !prev[expKey] }))}
          className={`p-0.5 rounded transition-colors ${theme.textSecondary} ${theme.hoverText}`}
          data-testid={`toggle-group-${group.key}`}
        >
          {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>
        <span className={`text-[11px] font-semibold uppercase tracking-wider flex-1 truncate ${theme.id === 'dark' ? 'text-[#00A1B2]/70' : 'text-[#00A1B2]'}`}>
          {group.label}
        </span>

        {/* "+" icon on hover to create page under this group */}
        <button
          onClick={(e) => { e.stopPropagation(); onCreateInGroup(group); }}
          className={`p-0.5 rounded transition-all opacity-0 group-hover/grp:opacity-100 ${theme.textSecondary} hover:text-[#00A1B2]`}
          title={`New page in ${group.label}`}
          data-testid={`add-page-in-group-${group.key}`}
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {isExpanded && (
        <div className="mt-0.5">
          {group.sections.map(sec => (
            <NavSection
              key={sec.key}
              section={sec}
              groupKey={group.key}
              sectionKey={sec.key}
              articles={sec.articles || []}
              selectedSlug={selectedSlug}
              onSelect={onSelect}
              expanded={expanded}
              setExpanded={setExpanded}
              onOpenSettings={onOpenSettings}
              onCreateInSection={onCreateInSection}
              theme={theme}
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
  onCreateInSection,
  onCreateInGroup,
  theme
}) => (
  <aside
    className={`w-64 flex-shrink-0 border-r ${theme.border} ${theme.panelBg} flex flex-col overflow-hidden`}
    style={theme.panelBgStyle}
    data-testid="editor-sidebar"
  >
    <div className={`px-3 py-3 flex items-center justify-between border-b ${theme.border}`}>
      <span className={`text-xs font-semibold ${theme.textSecondary} uppercase tracking-wider`}>Navigation</span>
      <button
        onClick={onNewCategory}
        className={`p-1 ${theme.textSecondary} hover:text-[#00A1B2] rounded transition-colors`}
        title="New category"
        data-testid="new-category-btn"
      >
        <Plus className="w-4 h-4" />
      </button>
    </div>
    <div className="flex-1 overflow-y-auto scrollbar-on-hover px-2 py-2">
      {tree.map(group => (
        <GroupItem
          key={group.key}
          group={group}
          selectedSlug={selectedSlug}
          onSelect={onSelect}
          expanded={expanded}
          setExpanded={setExpanded}
          onOpenSettings={onOpenSettings}
          onCreateInSection={onCreateInSection}
          onCreateInGroup={onCreateInGroup}
          theme={theme}
        />
      ))}
    </div>
  </aside>
);
