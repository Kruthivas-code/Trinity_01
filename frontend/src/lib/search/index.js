/**
 * Client-side instant search (Phase 5 of the help-doc-v3 feature port).
 * Ported from help-doc-v3's frontend/src/lib/search/index.js (FlexSearch),
 * trimmed to the fields Trinity's documents actually carry (no projectId/
 * icon filtering -- Trinity is a single KB, not multi-project) and reusing
 * Trinity's OWN heading parser (lib/mdx/parser.js's parseContent()) instead
 * of a second hand-rolled heading regex, same reuse AnchorsMenu.jsx (Phase
 * 4) already established for the same reason: one `# heading` -> id scheme
 * everywhere.
 *
 * Indexes both:
 *  - whole documents (title + stripped-markdown body) -> page-level hits
 *  - every heading of every document -> section-level hits with an anchor
 *    matching the id DocContent.jsx's h1-h4 renderers already generate, so
 *    a heading result can jump straight to `#that-id` on the page.
 */
import FlexSearch from 'flexsearch';
import { parseContent } from '../mdx/parser';

let documentIndex = null;
let headingIndex = null;
let searchData = new Map(); // slug -> { slug, title }

/** Strip markdown/HTML syntax down to plain text for indexing/snippets. */
function stripMarkdown(content) {
  if (!content) return '';
  return content
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')
    .replace(/<[^>]+>/g, '')
    .replace(/^#+\s+/gm, '')
    .replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function getSnippet(content, query, maxLength = 150) {
  const stripped = stripMarkdown(content);
  if (!stripped) return '';
  const idx = stripped.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) {
    return stripped.length > maxLength ? `${stripped.slice(0, maxLength)}...` : stripped;
  }
  const start = Math.max(0, idx - 50);
  const end = Math.min(stripped.length, idx + query.length + 100);
  let snippet = stripped.slice(start, end);
  if (start > 0) snippet = `...${snippet}`;
  if (end < stripped.length) snippet = `${snippet}...`;
  return snippet;
}

/** Build (or rebuild) the in-browser index from public-data's documents. */
export function initializeSearch(documents) {
  documentIndex = new FlexSearch.Document({
    document: { id: 'id', index: ['title', 'content'], store: ['title', 'slug'] },
    tokenize: 'forward',
    resolution: 9,
    cache: true,
  });
  headingIndex = new FlexSearch.Document({
    document: { id: 'id', index: ['text'], store: ['text', 'slug', 'docTitle', 'level', 'anchor'] },
    tokenize: 'forward',
    resolution: 9,
  });
  searchData = new Map();

  for (const doc of documents || []) {
    if (!doc?.slug) continue;
    const { headings } = parseContent(doc.content);
    documentIndex.add({ id: doc.slug, title: doc.title || '', content: stripMarkdown(doc.content || '') });
    searchData.set(doc.slug, { slug: doc.slug, title: doc.title || doc.slug });

    headings.forEach((h, i) => {
      headingIndex.add({
        id: `${doc.slug}__h${i}`,
        text: h.text,
        slug: doc.slug,
        docTitle: doc.title || doc.slug,
        level: h.level,
        anchor: h.id,
      });
    });
  }
}

export function clearSearch() {
  documentIndex = null;
  headingIndex = null;
  searchData = new Map();
}

/**
 * Search documents and headings. Returns { documents, headings }, both
 * capped at `limit`. Safe to call before initializeSearch() (e.g. while
 * public-data is still loading) -- just returns empty results.
 */
export function search(query, { limit = 8 } = {}) {
  if (!query || query.length < 2 || !documentIndex || !headingIndex) {
    return { documents: [], headings: [] };
  }

  const docResults = documentIndex.search(query, { limit: limit * 2, enrich: true });
  const headingResults = headingIndex.search(query, { limit: limit * 3, enrich: true });

  const documents = [];
  const seenDocs = new Set();
  for (const field of docResults) {
    for (const result of field.result) {
      if (seenDocs.has(result.id)) continue;
      const data = searchData.get(result.id);
      if (!data) continue;
      seenDocs.add(result.id);
      documents.push({
        slug: data.slug,
        title: data.title,
        snippet: getSnippet(result.doc?.content || '', query),
      });
    }
  }

  const headings = [];
  const seenHeadings = new Set();
  for (const field of headingResults) {
    for (const result of field.result) {
      if (seenHeadings.has(result.id)) continue;
      const d = result.doc;
      if (!d) continue;
      seenHeadings.add(result.id);
      headings.push({ slug: d.slug, text: d.text, docTitle: d.docTitle, anchor: d.anchor });
    }
  }

  return { documents: documents.slice(0, limit), headings: headings.slice(0, limit) };
}

export default { initializeSearch, search, clearSearch };
