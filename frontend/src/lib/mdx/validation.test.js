/**
 * Unit tests for Phase 7's content validation (frontend/src/lib/mdx/validation.js).
 * Run with `yarn test` (CRA/craco's built-in jest runner -- this is the
 * first test file in the frontend, added specifically for this module).
 */
import {
  validateDocument,
  validateProject,
  validateInternalLinks,
  validateComponents,
  formatValidationErrors,
  extractDocLinks,
  ValidationIssueType,
} from './validation';

const documents = [
  { slug: 'getting-started', title: 'Getting Started', published: true },
  { slug: 'draft-page', title: 'Draft Page', published: false },
];
const redirects = [
  { from_slug: 'old-getting-started', to_slug: 'getting-started' },
];

describe('extractDocLinks', () => {
  test('finds /docs/{slug} links with a slug boundary', () => {
    const md = 'See [here](/docs/getting-started) and <Card href="/docs/draft-page">go</Card>.';
    expect(extractDocLinks(md)).toEqual(['getting-started', 'draft-page']);
  });

  test('does not match a slug as a prefix of a longer one', () => {
    const md = 'Read [more](/docs/deployment-types) for details.';
    expect(extractDocLinks(md)).toEqual(['deployment-types']);
    expect(extractDocLinks(md)).not.toContain('deployment');
  });

  test('ignores links inside fenced code blocks', () => {
    const md = '```md\n[example](/docs/nope)\n```\nReal text.';
    expect(extractDocLinks(md)).toEqual([]);
  });
});

describe('validateInternalLinks', () => {
  test('a link to a live published page is clean', () => {
    const { errors, warnings } = validateInternalLinks(
      '[Start here](/docs/getting-started)', { documents, redirects }
    );
    expect(errors).toHaveLength(0);
    expect(warnings).toHaveLength(0);
  });

  test('a link to a slug covered by a redirect is a warning, not an error', () => {
    const { errors, warnings } = validateInternalLinks(
      '[Start here](/docs/old-getting-started)', { documents, redirects }
    );
    expect(errors).toHaveLength(0);
    expect(warnings).toHaveLength(1);
    expect(warnings[0].type).toBe(ValidationIssueType.REDIRECTED_LINK);
    expect(warnings[0].redirectsTo).toBe('getting-started');
  });

  test('a link to a slug with no article and no redirect is an error', () => {
    const { errors } = validateInternalLinks(
      '[Nowhere](/docs/totally-made-up)', { documents, redirects }
    );
    expect(errors).toHaveLength(1);
    expect(errors[0].type).toBe(ValidationIssueType.BROKEN_LINK);
  });

  test('a link to an unpublished draft page is a warning', () => {
    const { errors, warnings } = validateInternalLinks(
      '[Draft](/docs/draft-page)', { documents, redirects }
    );
    expect(errors).toHaveLength(0);
    expect(warnings).toHaveLength(1);
    expect(warnings[0].type).toBe(ValidationIssueType.UNPUBLISHED_LINK);
  });
});

describe('validateComponents', () => {
  test('the real component vocabulary passes clean', () => {
    const md = [
      '<Callout type="tip" title="Heads up">Body</Callout>',
      '<Steps><Step title="Install">do it</Step></Steps>',
      '<CardGroup><Card title="A" icon="rocket" href="/docs/getting-started">desc</Card></CardGroup>',
      '<Tabs><Tab label="JS">code</Tab></Tabs>',
    ].join('\n');
    const { errors, warnings } = validateComponents(md);
    expect(errors).toHaveLength(0);
    expect(warnings).toHaveLength(0);
  });

  test('flags <CardGroup cols={2}> as the known Mintlify-style mistake', () => {
    const { errors } = validateComponents('<CardGroup cols={2}><Card title="A">x</Card></CardGroup>');
    expect(errors.some(e => e.type === ValidationIssueType.MINTLIFY_CARDGROUP_COLS)).toBe(true);
  });

  test('flags <Tab title="..."> as the known Mintlify-style mistake', () => {
    const { errors } = validateComponents('<Tabs><Tab title="JS">code</Tab></Tabs>');
    expect(errors.some(e => e.type === ValidationIssueType.MINTLIFY_TAB_TITLE)).toBe(true);
  });

  test('flags an unknown/unsupported component tag', () => {
    const { errors } = validateComponents('<Warning2 type="foo">nope</Warning2>');
    expect(errors.some(e => e.type === ValidationIssueType.UNKNOWN_COMPONENT)).toBe(true);
  });

  test('warns on out-of-order Card attributes', () => {
    const { warnings } = validateComponents('<Card icon="rocket" title="A" href="/docs/x">desc</Card>');
    expect(warnings.some(w => w.type === ValidationIssueType.CARD_PROP_ORDER)).toBe(true);
  });

  test('does not flag components mentioned inside a fenced code example', () => {
    const md = '```mdx\n<CardGroup cols={2}>\n```';
    const { errors } = validateComponents(md);
    expect(errors).toHaveLength(0);
  });
});

describe('validateDocument', () => {
  const validArticle = {
    title: 'Getting Started',
    slug: 'getting-started',
    description: 'How to get started.',
    content_markdown: '<Callout type="tip">Welcome!</Callout>\n\nSome body text.',
    published: true,
  };

  test('a well-formed published article is valid with no findings', () => {
    const result = validateDocument(validArticle, { documents, redirects });
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.warnings).toHaveLength(0);
    expect(result.info.wordCount).toBeGreaterThan(0);
  });

  test('missing title and invalid slug are errors', () => {
    const result = validateDocument({ title: '', slug: 'Not A Slug!', content_markdown: 'x', published: false });
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.type === ValidationIssueType.MISSING_TITLE)).toBe(true);
    expect(result.errors.some(e => e.type === ValidationIssueType.INVALID_SLUG)).toBe(true);
  });

  test('a published page with empty content is an error', () => {
    const result = validateDocument({ title: 'T', slug: 'empty-page', content_markdown: '  ', published: true });
    expect(result.errors.some(e => e.type === ValidationIssueType.EMPTY_PUBLISHED_CONTENT)).toBe(true);
  });

  test('a published page with no description is a warning, not an error', () => {
    const result = validateDocument({ title: 'T', slug: 'no-desc', content_markdown: 'body', published: true, description: '' });
    expect(result.errors).toHaveLength(0);
    expect(result.warnings.some(w => w.type === ValidationIssueType.MISSING_DESCRIPTION)).toBe(true);
  });

  test('an unpublished draft tolerates a missing description', () => {
    const result = validateDocument({ title: 'T', slug: 'draft', content_markdown: '', published: false, description: '' });
    expect(result.valid).toBe(true);
  });

  test('a broken internal link surfaces as an error via context', () => {
    const article = { ...validArticle, content_markdown: '[Nope](/docs/does-not-exist)' };
    const result = validateDocument(article, { documents, redirects });
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.type === ValidationIssueType.BROKEN_LINK)).toBe(true);
  });

  test('strictMode promotes warnings to errors', () => {
    const article = { ...validArticle, description: '' };
    const loose = validateDocument(article, { documents, redirects });
    const strict = validateDocument(article, { documents, redirects, strictMode: true });
    expect(loose.valid).toBe(true);
    expect(loose.warnings.length).toBeGreaterThan(0);
    expect(strict.valid).toBe(false);
    expect(strict.warnings).toHaveLength(0);
  });
});

describe('validateProject', () => {
  test('aggregates errors/warnings across all documents', () => {
    const project = [
      { slug: 'getting-started', title: 'Getting Started', published: true, description: 'd', content_markdown: 'ok body' },
      { slug: 'broken', title: 'Broken', published: true, description: 'd', content_markdown: '[x](/docs/nowhere)' },
    ];
    const result = validateProject(project, redirects);
    expect(result.valid).toBe(false);
    expect(result.totalErrors).toBeGreaterThan(0);
    expect(result.documents).toHaveLength(2);
  });
});

describe('formatValidationErrors', () => {
  test('attaches a formatted SEVERITY: message string', () => {
    const [formatted] = formatValidationErrors([
      { type: ValidationIssueType.MISSING_TITLE, severity: 'error', message: 'Title is required.' },
    ]);
    expect(formatted.formatted).toBe('ERROR: Title is required.');
  });
});
