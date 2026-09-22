/**
 * RelatedPages - "Related pages" section for the bottom of an article
 * (Phase 5 of the help-doc-v3 feature port).
 *
 * help-doc-v3's ConceptNav (frontend/src/components/docs/ConceptNav.jsx) is
 * a full concept-graph *navigation tree* built by buildConceptGraph()
 * (lib/mdx/parser.js): it links documents that share a frontmatter `tag`
 * (extractTags(doc.content)) and documents related by an explicit
 * `doc.parent_id`. Trinity has neither a parent_id field nor a frontmatter
 * tag block on kb_articles (see ArticleUpdate in routes/kb.py) -- the
 * closest equivalents Trinity's articles actually carry are:
 *   - nav_group_key / section_key: the article's tab/group position in the
 *     recursive nav tree (denormalized onto kb_articles -- see kb.py's
 *     "Each kb_articles document keeps denormalized nav_group_key/..."
 *     comment), which is structurally the same signal as ConceptNav's
 *     parent-child edges (documents filed together).
 *   - keywords / tags: free-form lists on ArticleUpdate, the direct
 *     equivalent of ConceptNav's shared-tag edges.
 * So instead of porting ConceptNav's own tree-building (which trinity
 * doesn't need -- Phase 0 already has a working nav tree; see
 * PublicDocs.jsx's flattenGroupPages/findPageGroup), this ports just its
 * "related documents" idea as a simple, explainable heuristic:
 *   score = (+3 same section_key) or (+1 same nav_group_key, if not already
 *            scored via section_key) + 2 * (number of shared keywords/tags)
 * ranked descending, top 5, self excluded. A page with no group/tag signal
 * in common with anything else renders nothing (not an empty box).
 */
import { useMemo } from 'react';
import { Link2, FileText } from 'lucide-react';

const normTagSet = (doc) => {
  const raw = [...(doc?.keywords || []), ...(doc?.tags || [])];
  return new Set(raw.map((t) => String(t || '').trim().toLowerCase()).filter(Boolean));
};

export function computeRelated(currentDoc, documents, limit = 5) {
  if (!currentDoc || !Array.isArray(documents) || documents.length === 0) return [];
  const currentTags = normTagSet(currentDoc);
  const scored = [];

  for (const doc of documents) {
    if (!doc || doc.slug === currentDoc.slug) continue;
    let score = 0;
    if (currentDoc.section_key && doc.section_key && currentDoc.section_key === doc.section_key) {
      score += 3;
    } else if (currentDoc.nav_group_key && doc.nav_group_key && currentDoc.nav_group_key === doc.nav_group_key) {
      score += 1;
    }
    let shared = 0;
    const docTags = normTagSet(doc);
    for (const t of docTags) if (currentTags.has(t)) shared += 1;
    score += shared * 2;

    if (score > 0) scored.push({ doc, score });
  }

  scored.sort((a, b) => b.score - a.score || (a.doc.order ?? 0) - (b.doc.order ?? 0));
  return scored.slice(0, limit).map((s) => s.doc);
}

export const RelatedPages = ({ currentDoc, documents, onSelect, theme }) => {
  const related = useMemo(() => computeRelated(currentDoc, documents), [currentDoc, documents]);
  if (related.length === 0) return null;

  const isDark = theme?.id === 'dark';

  return (
    <div className={`mt-12 pt-8 border-t ${theme?.border || 'border-gray-200 dark:border-white/10'}`} data-testid="kb-related-pages">
      <h3 className={`text-xs font-semibold uppercase tracking-wider mb-4 flex items-center gap-1.5 ${theme?.textMuted || 'text-gray-500'}`}>
        <Link2 className="w-3.5 h-3.5" />
        Related pages
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {related.map((doc) => (
          <button
            key={doc.slug}
            onClick={() => onSelect(doc.slug)}
            className={`flex items-center gap-2.5 px-4 py-3 rounded-lg border text-left transition-colors ${theme?.border || 'border-gray-200 dark:border-white/10'} ${
              isDark ? 'hover:bg-white/5' : 'hover:bg-gray-50'
            }`}
            data-testid={`related-page-${doc.slug}`}
          >
            <FileText className={`w-4 h-4 flex-shrink-0 ${theme?.textSecondary || 'text-gray-400'}`} />
            <span className={`text-sm font-medium truncate ${theme?.text || 'text-gray-900 dark:text-white'}`}>{doc.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default RelatedPages;
