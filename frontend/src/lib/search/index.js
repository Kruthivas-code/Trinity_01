/**
 * Client-side search using FlexSearch
 */
import FlexSearch from 'flexsearch';

let documentIndex = null;
let headingIndex = null;
let searchData = new Map();

export function initializeSearch(documents) {
  documentIndex = new FlexSearch.Document({
    document: { id: 'id', index: ['title', 'content'], store: ['title', 'slug'] },
    tokenize: 'forward',
    resolution: 9,
    cache: true,
  });
  headingIndex = new FlexSearch.Document({
    document: { id: 'id', index: ['text'], store: ['text', 'docId', 'docTitle', 'slug', 'level'] },
    tokenize: 'forward',
    resolution: 9,
  });
  searchData.clear();

  for (const doc of documents) {
    const headings = extractHeadings(doc.content);
    documentIndex.add({ id: doc.id, title: doc.title, content: stripMarkdown(doc.content || ''), slug: doc.slug });
    searchData.set(doc.id, { id: doc.id, title: doc.title, slug: doc.slug, headings });
    headings.forEach((h, i) => {
      headingIndex.add({ id: `${doc.id}-h-${i}`, text: h.text, docId: doc.id, docTitle: doc.title, slug: doc.slug, level: h.level });
    });
  }
}

export function search(query) {
  if (!query || query.length < 2 || !documentIndex) return { documents: [], headings: [] };
  const docResults = documentIndex.search(query, { limit: 20, enrich: true });
  const headingResults = headingIndex.search(query, { limit: 30, enrich: true });

  const documents = [];
  const seenDocs = new Set();
  for (const field of docResults) {
    for (const result of field.result) {
      if (seenDocs.has(result.id)) continue;
      const docData = searchData.get(result.id);
      if (!docData) continue;
      seenDocs.add(result.id);
      documents.push({ id: result.id, title: docData.title, slug: docData.slug, snippet: getSnippet(result.doc?.content || '', query) });
    }
  }

  const headings = [];
  const seenH = new Set();
  for (const field of headingResults) {
    for (const result of field.result) {
      if (seenH.has(result.id)) continue;
      const doc = result.doc;
      if (!doc) continue;
      seenH.add(result.id);
      headings.push({ id: result.id, text: doc.text, docId: doc.docId, docTitle: doc.docTitle, slug: doc.slug, level: doc.level, anchor: doc.text.toLowerCase().replace(/[^a-z0-9]+/g, '-') });
    }
  }

  return { documents: documents.slice(0, 10), headings: headings.slice(0, 10) };
}

function extractHeadings(content) {
  if (!content) return [];
  const headings = [];
  const regex = /^(#{1,6})\s+(.+)$/gm;
  let match;
  while ((match = regex.exec(content)) !== null) headings.push({ level: match[1].length, text: match[2].trim() });
  return headings;
}

function stripMarkdown(content) {
  return content.replace(/```[\s\S]*?```/g, '').replace(/`[^`]+`/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/<[^>]+>/g, '').replace(/^#+\s+/gm, '').replace(/[*_]{1,3}([^*_]+)[*_]{1,3}/g, '$1').replace(/\s+/g, ' ').trim();
}

function getSnippet(content, query, maxLength = 150) {
  if (!content) return '';
  const stripped = stripMarkdown(content);
  const idx = stripped.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return stripped.slice(0, maxLength) + (stripped.length > maxLength ? '...' : '');
  const start = Math.max(0, idx - 50);
  const end = Math.min(stripped.length, idx + query.length + 100);
  let snippet = stripped.slice(start, end);
  if (start > 0) snippet = '...' + snippet;
  if (end < stripped.length) snippet += '...';
  return snippet;
}
