/**
 * Review Mode E2E Tests
 * Tests for the PM review workflow: /dashboard/review (console) and
 * /dashboard/review/:slug (per-page review — comments, verdicts, publish gate).
 *
 * Like the rest of this suite, these assume a pre-seeded session for
 * SESSION_TOKEN already exists in the target environment's database — they
 * cannot authenticate against a fresh/empty database on their own.
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://repo-builder-83.preview.emergentagent.com';
const ADMIN_SESSION_TOKEN = 'test_review_mode_admin_session';
const REVIEWER_SESSION_TOKEN = 'test_review_mode_reviewer_session';

async function authenticateAs(page: Page, token: string) {
  await page.context().addCookies([{
    name: 'session_token',
    value: token,
    domain: 'docs-rebuild-polish.preview.emergentagent.com',
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'None',
  }]);
}

test.describe('Review Console — admin', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAs(page, ADMIN_SESSION_TOKEN);
    await page.goto('/dashboard/review', { waitUntil: 'domcontentloaded' });
  });

  test('console loads with all tabs visible to an admin', async ({ page }) => {
    await expect(page.getByTestId('tab-overview')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('tab-assignments')).toBeVisible();
    await expect(page.getByTestId('tab-inbox')).toBeVisible();
    await expect(page.getByTestId('tab-mis')).toBeVisible();
    await expect(page.getByTestId('tab-activity')).toBeVisible();
  });

  test('assignments tab shows the create-assignment form for an admin', async ({ page }) => {
    await page.getByTestId('tab-assignments').click();
    await expect(page.getByTestId('create-assignment-btn')).toBeVisible();
  });

  test('MIS dashboard loads funnel and reviewer stats', async ({ page }) => {
    await page.getByTestId('tab-mis').click();
    await expect(page.getByText('Total pages')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Reviewers')).toBeVisible();
    await expect(page.getByText('Images missing alt text')).toBeVisible();
  });

  test('inbox tab is visible and lists comments for an admin', async ({ page }) => {
    await page.getByTestId('tab-inbox').click();
    // Either a comment row or the empty state — both prove the tab rendered without crashing.
    await expect(
      page.getByText(/No comments yet\.|open|resolved/i).first()
    ).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Review Console — reviewer (non-admin)', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAs(page, REVIEWER_SESSION_TOKEN);
    await page.goto('/dashboard/review', { waitUntil: 'domcontentloaded' });
  });

  test('admin-only tabs are hidden for a reviewer', async ({ page }) => {
    await expect(page.getByTestId('tab-overview')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('tab-assignments')).toBeVisible();
    await expect(page.getByTestId('tab-mis')).toBeVisible();
    await expect(page.getByTestId('tab-inbox')).toHaveCount(0);
    await expect(page.getByTestId('tab-activity')).toHaveCount(0);
  });

  test('assignments tab hides the create-assignment form for a reviewer', async ({ page }) => {
    await page.getByTestId('tab-assignments').click();
    await expect(page.getByTestId('create-assignment-btn')).toHaveCount(0);
  });
});

test.describe('Review Page — comments, verdicts, publish gate', () => {
  // These assume a KB article with slug "getting-started" already exists in the
  // target environment (seeded the same way the kb-* spec files' fixtures are).
  const SLUG = 'getting-started';

  test.beforeEach(async ({ page }) => {
    await authenticateAs(page, ADMIN_SESSION_TOKEN);
    await page.goto(`/dashboard/review/${SLUG}`, { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('review-page')).toBeVisible({ timeout: 15000 });
  });

  test('page loads with content, comments rail, and verdict picker', async ({ page }) => {
    await expect(page.getByTestId('review-content')).toBeVisible();
    await expect(page.getByTestId('review-comments-rail')).toBeVisible();
    await expect(page.getByTestId('reviewpage-verdict-Looks-correct')).toBeVisible();
  });

  test('adding a top-level comment shows it in the comments rail', async ({ page }) => {
    const body = `E2E test comment ${Date.now()}`;
    await page.getByTestId('new-comment-input').fill(body);
    await page.getByTestId('new-comment-submit').click();
    await expect(page.getByText(body)).toBeVisible({ timeout: 10000 });
  });

  test('resolving a comment flips it to the resolved state', async ({ page }) => {
    const body = `E2E resolve-test comment ${Date.now()}`;
    await page.getByTestId('new-comment-input').fill(body);
    await page.getByTestId('new-comment-submit').click();

    const commentRow = page.locator(`[data-testid^="review-comment-"]`).filter({ hasText: body });
    await expect(commentRow).toBeVisible({ timeout: 10000 });
    await commentRow.getByText('Resolve').click();
    await expect(commentRow.getByText('Reopen')).toBeVisible({ timeout: 10000 });
  });

  test('setting a verdict persists and shows the "Set by" attribution', async ({ page }) => {
    await page.getByTestId('reviewpage-verdict-Needs-small-edits').click();
    await expect(page.getByTestId('verdict-set-by')).toBeVisible({ timeout: 10000 });

    // Reload and confirm the verdict was actually persisted server-side, not just local state.
    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('verdict-set-by')).toBeVisible({ timeout: 15000 });
  });

  test('page history panel opens and closes', async ({ page }) => {
    await page.getByTestId('reviewpage-history-btn').click();
    await expect(page.getByTestId('page-history-panel')).toBeVisible({ timeout: 10000 });
    await page.getByTestId('page-history-close').click();
    await expect(page.getByTestId('page-history-panel')).toHaveCount(0);
  });
});

test.describe('Publish gate', () => {
  // Uses a page seeded with at least one *unresolved* review comment
  // (mirrors the fixture convention other kb-*.spec.ts files rely on).
  const SLUG_WITH_OPEN_COMMENT = 'deploying-your-app';

  test('publish is blocked while a comment is unresolved', async ({ page, request }) => {
    await authenticateAs(page, ADMIN_SESSION_TOKEN);
    const res = await request.post(`${BASE_URL}/api/review/articles/${SLUG_WITH_OPEN_COMMENT}/publish`, {
      headers: { Cookie: `session_token=${ADMIN_SESSION_TOKEN}` },
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.detail).toMatch(/open comment/i);
  });

  test('non-admin cannot publish at all', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/api/review/articles/${SLUG_WITH_OPEN_COMMENT}/publish`, {
      headers: { Cookie: `session_token=${REVIEWER_SESSION_TOKEN}` },
    });
    expect(res.status()).toBe(403);
  });
});
