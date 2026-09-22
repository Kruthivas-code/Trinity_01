/**
 * MDX Validation (Phase 7 of the help-doc-v3 feature port).
 *
 * Ported from help-doc-v3's frontend/src/lib/mdx/validation.js, but rebuilt
 * against Trinity's REAL data model and component vocabulary rather than
 * transliterated field-for-field -- help-doc-v3's version assumes a `doc`
 * object with generic `{ id, content }` shape and a component/link checker
 * driven by ITS OWN parser's `ValidationError` enum (frontend/src/lib/mdx/
 * parser.js in help-doc-v3), neither of which exist here:
 *
 *  - Trinity's parser (./parser.js) is a much simpler regex-based
 *    heading/component extractor reused by AnchorsMenu (Phase 4) and the
 *    search indexer (Phase 5). It has no error/severity concept at all, so
 *    this file owns its own lightweight "finding" shape
 *    ({ type, severity, message }) instead of importing one.
 *  - Trinity's article fields are the `ArticleUpdate`/`ArticleCreate` set
 *    from backend/routes/kb.py: title, slug, description, section_key,
 *    nav_group_key, content_markdown, published, order, icon,
 *    sidebar_title, keywords, tags. There is no help-doc-v3-style generic
 *    `doc.content` -- checks below read `content_markdown` and factor in
 *    `published` (an unpublished page tolerates gaps a live one shouldn't).
 *  - Trinity's internal links are root-relative `/docs/{slug}` (confirmed
 *    against backend/routes/kb.py's own `_internal_link_regex`, which this
 *    file's DOC_LINK_PATTERN mirrors byte-for-byte: same slug boundary
 *    chars `)"'#?` + whitespace/end-of-string, same slug charset
 *    `[a-z0-9][a-z0-9-]*`) -- NOT help-doc-v3's bare `/{slug}`.
 *  - Trinity's component vocabulary is COMPONENT_GUIDE in
 *    backend/routes/assistant.py (Phase 3's ground truth for what the AI
 *    assistant is told to write, and therefore also ground truth for what
 *    this platform's markdown renderer actually understands). It diverges
 *    from help-doc-v3/Mintlify in ways worth checking for explicitly:
 *    bare <CardGroup> (never `cols={n}`), <Tab label="..."> (never
 *    `title="..."`), bare <Steps>/<Accordion> outer tags, etc.
 */

import { parseContent } from './parser';

// ── Finding helpers ─────────────────────────────────────────────────────

/** Machine-readable finding types, used by callers that want to filter/key
 * on a specific check rather than just the human message. */
export const ValidationIssueType = {
  MISSING_TITLE: 'missing_title',
  MISSING_SLUG: 'missing_slug',
  INVALID_SLUG: 'invalid_slug',
  EMPTY_PUBLISHED_CONTENT: 'empty_published_content',
  MISSING_DESCRIPTION: 'missing_description',
  BROKEN_LINK: 'broken_link',
  REDIRECTED_LINK: 'redirected_link',
  UNPUBLISHED_LINK: 'unpublished_link',
  UNKNOWN_COMPONENT: 'unknown_component',
  MINTLIFY_CARDGROUP_COLS: 'mintlify_cardgroup_cols',
  MINTLIFY_TAB_TITLE: 'mintlify_tab_title',
  CARD_PROP_ORDER: 'card_prop_order',
};

function finding(type, severity, message, extra = {}) {
  return { type, severity, message, ...extra };
}

/** Strip fenced code blocks before scanning raw markdown for component tags
 * or links, so a doc that's ABOUT this platform's syntax (e.g. a snippet
 * showing the wrong `<Tab title="...">` as a cautionary example) doesn't
 * trip these checks on text that's never actually rendered as a component. */
function stripCodeFences(content) {
  return (content || '').replace(/```[\s\S]*?```/g, '');
}

// ── Internal links ──────────────────────────────────────────────────────

// Mirrors backend/routes/kb.py's `_internal_link_regex(slug)` /
// `SLUG_PATTERN` exactly: `/docs/` + a valid slug + the same boundary set
// (closing paren/quote, `#`, `?`, whitespace, or end of string) so a hit on
// `/docs/deployment` never also matches `/docs/deployment-types`. Unlike
// help-doc-v3's `[text](/docs/slug)`-only pattern, this deliberately is
// NOT limited to Markdown link syntax -- it also has to catch
// `<Card href="/docs/slug">`, which is the actual, common link shape inside
// CardGroup/Columns content on this platform (backend/routes/kb.py's own
// slug-rename rewrite scans the same way, for the same reason).
export const DOC_LINK_PATTERN = /\/docs\/([a-z0-9][a-z0-9-]*)(?=[)"'#?\s]|$)/g;

/** Every `/docs/{slug}` occurrence in `content`, as plain slugs. */
export function extractDocLinks(content) {
  const found = [];
  const pattern = new RegExp(DOC_LINK_PATTERN.source, 'g');
  let m;
  while ((m = pattern.exec(stripCodeFences(content))) !== null) {
    found.push(m[1]);
  }
  return found;
}

/**
 * Validate `/docs/{slug}` links in `content` against the real, current set
 * of link targets:
 *   - a slug backed by a PUBLISHED, live article -> fine, no finding.
 *   - a slug backed by an unpublished (draft) article -> warning: the link
 *     itself is intentional and will resolve once that page ships, but it
 *     404s on the public site right now.
 *   - a slug with no live article, but a working redirect chain from
 *     Phase 4's kb_redirects (surfaced to the frontend as public-data's
 *     `redirects: [{from_slug, to_slug}]`) -> warning, not an error: Phase 4
 *     made these non-broken (PublicDocs.jsx follows the same redirect list
 *     client-side), the link just isn't pointing at the canonical slug
 *     anymore.
 *   - anything else -> error: the link 404s on the public site with no
 *     recovery path.
 *
 * `context.documents` is the article list shape already used throughout
 * this codebase (public-data's `documents`, or admin `GET /admin/articles`'s
 * `articles` -- either works, only `.slug`/`.published` are read).
 * `context.redirects` is public-data's `redirects` field verbatim.
 */
export function validateInternalLinks(content, context = {}) {
  const errors = [];
  const warnings = [];
  if (!content) return { errors, warnings };

  const documents = context.documents || [];
  const redirects = context.redirects || [];
  const publishedSlugs = new Set(
    documents.filter(d => d.published !== false).map(d => d.slug)
  );
  const draftSlugs = new Set(
    documents.filter(d => d.published === false).map(d => d.slug)
  );
  const redirectSlugs = new Set(redirects.map(r => r.from_slug));

  const seen = new Set(); // de-dupe repeated links to the same bad target
  for (const slug of extractDocLinks(content)) {
    if (publishedSlugs.has(slug)) continue;
    const key = slug;
    if (seen.has(key)) continue;

    if (redirectSlugs.has(slug)) {
      seen.add(key);
      const target = redirects.find(r => r.from_slug === slug)?.to_slug;
      warnings.push(finding(
        ValidationIssueType.REDIRECTED_LINK,
        'warning',
        `Link to /docs/${slug} goes through a redirect (now /docs/${target}). It still works, but consider pointing it at the current slug directly.`,
        { slug, redirectsTo: target }
      ));
    } else if (draftSlugs.has(slug)) {
      seen.add(key);
      warnings.push(finding(
        ValidationIssueType.UNPUBLISHED_LINK,
        'warning',
        `Link to /docs/${slug} points at a page that isn't published yet.`,
        { slug }
      ));
    } else {
      seen.add(key);
      errors.push(finding(
        ValidationIssueType.BROKEN_LINK,
        'error',
        `Broken internal link: /docs/${slug} doesn't match any known page or redirect.`,
        { slug }
      ));
    }
  }

  return { errors, warnings };
}

// ── Component usage ─────────────────────────────────────────────────────

// The exact set of platform-recognized component/tag names, straight out of
// COMPONENT_GUIDE in backend/routes/assistant.py (Phase 3's ground truth --
// the AI assistant is instructed with this same list, "use ONLY these --
// they render natively; anything else falls through as literal text").
// `iframe` is excluded here on purpose: it's plain lowercase HTML, not one
// of this platform's capitalized components, and is always allowed as-is.
const KNOWN_COMPONENTS = new Set([
  'Callout',
  'Note', 'Info', 'Tip', 'Warning', 'Caution', 'Error', 'Danger', 'Success', // Callout shorthands
  'Steps', 'Step',
  'CardGroup', 'Card',
  'Columns', 'ColumnLayout', 'Col',
  'Tabs', 'Tab',
  'Accordion', 'AccordionItem',
  'YouTube', 'Loom', 'Video', 'Figure',
]);

// Opening/self-closing JSX-like tags only (capitalized -- this platform's
// components are always capitalized per COMPONENT_GUIDE); closing tags
// `</Foo>` never match since they don't start with `<` + an uppercase
// letter.
const OPEN_TAG_PATTERN = /<([A-Z][A-Za-z0-9]*)((?:\s+[^<>]*?)?)\/?>/g;

const CARD_PROP_ORDER = ['title', 'icon', 'href'];

/** Does `attrs` (the raw text between the tag name and `>`) declare `name=`? */
function hasProp(attrs, name) {
  return new RegExp(`\\b${name}\\s*=`).test(attrs);
}

/** Attribute names in the order they actually appear in `attrs`. */
function propOrder(attrs) {
  const order = [];
  const re = /([A-Za-z][\w-]*)\s*=/g;
  let m;
  while ((m = re.exec(attrs)) !== null) order.push(m[1]);
  return order;
}

/**
 * Validate component/tag usage in `content` against COMPONENT_GUIDE's real
 * vocabulary. Flags:
 *   - any capitalized tag that isn't in KNOWN_COMPONENTS (error -- it falls
 *     through as literal text on this platform, per COMPONENT_GUIDE rule 1).
 *   - `<CardGroup cols={n}>` (error) -- COMPONENT_GUIDE explicitly calls
 *     this out as a Mintlify-style mistake this platform doesn't parse;
 *     CardGroup takes no attributes here.
 *   - `<Tab title="...">` (error) -- same call-out: this platform's Tab
 *     uses `label`, never `title`.
 *   - `<Card>` whose attributes aren't in title/icon/href order (warning --
 *     COMPONENT_GUIDE documents a required order for Cards inside a
 *     CardGroup; downgraded to a warning here since, unlike the two errors
 *     above, the guide doesn't say this variant fails to render).
 */
export function validateComponents(content) {
  const errors = [];
  const warnings = [];
  if (!content) return { errors, warnings };

  const scanned = stripCodeFences(content);
  const pattern = new RegExp(OPEN_TAG_PATTERN.source, 'g');
  let m;
  while ((m = pattern.exec(scanned)) !== null) {
    const tag = m[1];
    const attrs = m[2] || '';

    if (tag === 'CardGroup' && hasProp(attrs, 'cols')) {
      errors.push(finding(
        ValidationIssueType.MINTLIFY_CARDGROUP_COLS,
        'error',
        `<CardGroup cols={...}> isn't valid here -- CardGroup takes no attributes on this platform (use <Columns cols={n}> for side-by-side layout instead). This renders as broken literal text.`,
        { tag }
      ));
      continue;
    }

    if (tag === 'Tab' && hasProp(attrs, 'title')) {
      errors.push(finding(
        ValidationIssueType.MINTLIFY_TAB_TITLE,
        'error',
        `<Tab title="..."> isn't valid here -- use <Tab label="..."> instead. This renders as broken literal text.`,
        { tag }
      ));
      continue;
    }

    if (!KNOWN_COMPONENTS.has(tag)) {
      errors.push(finding(
        ValidationIssueType.UNKNOWN_COMPONENT,
        'error',
        `Unknown component <${tag}>. It isn't in this platform's supported vocabulary and will render as literal text.`,
        { tag }
      ));
      continue;
    }

    if (tag === 'Card') {
      const order = propOrder(attrs).filter(p => CARD_PROP_ORDER.includes(p));
      const expected = CARD_PROP_ORDER.filter(p => order.includes(p));
      if (order.some((p, i) => p !== expected[i])) {
        warnings.push(finding(
          ValidationIssueType.CARD_PROP_ORDER,
          'warning',
          `<Card> attributes should be ordered title, icon, href; found ${order.join(', ')}.`,
          { tag }
        ));
      }
    }
  }

  return { errors, warnings };
}

// ── Document-level validation ───────────────────────────────────────────

// Mirrors backend/routes/kb.py's SLUG_PATTERN exactly.
const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]*$/;

/**
 * Validate one article against Trinity's real `ArticleUpdate` field set.
 * `article` is the editor's in-memory form / a stored article doc (reads
 * title, slug, description, content_markdown, published only -- the other
 * ArticleUpdate fields, section_key/nav_group_key/order/icon/sidebar_title/
 * keywords/tags, don't have meaningful "valid vs invalid" shapes worth
 * linting here).
 *
 * `context.documents` / `context.redirects`, when provided, feed
 * validateInternalLinks (same shapes as that function takes). `context.
 * strictMode` promotes every warning to an error, same concept as
 * help-doc-v3's original.
 */
export function validateDocument(article, context = {}) {
  const errors = [];
  const warnings = [];

  const title = (article?.title || '').trim();
  const slug = (article?.slug || '').trim();
  const description = (article?.description || '').trim();
  const content = article?.content_markdown || '';
  const published = !!article?.published;

  if (!title) {
    errors.push(finding(ValidationIssueType.MISSING_TITLE, 'error', 'Title is required.'));
  }

  if (!slug) {
    errors.push(finding(ValidationIssueType.MISSING_SLUG, 'error', 'Slug is required.'));
  } else if (!SLUG_PATTERN.test(slug)) {
    errors.push(finding(
      ValidationIssueType.INVALID_SLUG,
      'error',
      `Slug "${slug}" is invalid -- use lowercase letters, numbers and hyphens, starting with a letter or number.`
    ));
  }

  if (published && !content.trim()) {
    errors.push(finding(ValidationIssueType.EMPTY_PUBLISHED_CONTENT, 'error', 'This page is published but has no content.'));
  }

  if (published && !description) {
    warnings.push(finding(ValidationIssueType.MISSING_DESCRIPTION, 'warning', 'Published page has no description (used for SEO and card/link previews).'));
  }

  const componentResult = validateComponents(content);
  errors.push(...componentResult.errors);
  warnings.push(...componentResult.warnings);

  if (context.documents || context.redirects) {
    const linkResult = validateInternalLinks(content, context);
    errors.push(...linkResult.errors);
    warnings.push(...linkResult.warnings);
  }

  if (context.strictMode) {
    errors.push(...warnings);
    warnings.length = 0;
  }

  const { headings } = parseContent(content);

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    info: {
      headingCount: headings.length,
      wordCount: content ? content.trim().split(/\s+/).filter(Boolean).length : 0,
    },
  };
}

/**
 * Validate every article in a project (all of GET /admin/articles's
 * `articles`, or public-data's `documents`) against each other -- each
 * article's internal links are checked against the full set, so a link to
 * a page that exists elsewhere in the project is never flagged just because
 * that one article was validated in isolation.
 *
 * `redirects` is public-data's `redirects` list; optional (an admin-side
 * caller that hasn't fetched public-data can validate structure/components
 * without it, just with weaker link-redirect awareness).
 */
export function validateProject(documents, redirects = []) {
  const results = {
    valid: true,
    totalErrors: 0,
    totalWarnings: 0,
    documents: [],
  };

  const context = { documents, redirects };

  for (const doc of documents || []) {
    const docResult = validateDocument(doc, context);
    results.documents.push({ slug: doc.slug, title: doc.title, ...docResult });
    if (!docResult.valid) results.valid = false;
    results.totalErrors += docResult.errors.length;
    results.totalWarnings += docResult.warnings.length;
  }

  return results;
}

/** Presentation helper: attach a "SEVERITY: message" formatted string to
 * each finding, for a quick inline list/toast (no positions to report --
 * Trinity's parser.js doesn't track them, unlike help-doc-v3's). */
export function formatValidationErrors(findings) {
  return (findings || []).map(f => ({
    ...f,
    formatted: `${f.severity.toUpperCase()}: ${f.message}`,
  }));
}

export default {
  validateDocument,
  validateProject,
  validateInternalLinks,
  validateComponents,
  formatValidationErrors,
  extractDocLinks,
  ValidationIssueType,
};
