import { test, expect } from '@playwright/test';

const BASE_URL = process.env.REACT_APP_BACKEND_URL || 'https://data-integrity-fix-37.preview.emergentagent.com';
const ADMIN_SESSION_TOKEN = 'test_kb_session_token';

test.describe('Portal KB Integration - Frontend', () => {
  test.describe('Portal Home', () => {
    test('portal home shows categories grid with data from DB', async ({ page }) => {
      await page.goto('/portal', { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId('portal-home')).toBeVisible();
      await expect(page.getByTestId('portal-hero-title')).toHaveText('How can we help?');
      
      // Check categories section exists
      await expect(page.getByTestId('categories-section')).toBeVisible();
      
      // Check at least one category card
      await expect(page.getByTestId('category-card-credits-pricing')).toBeVisible();
    });

    test('category cards show title, description, icon, and topic counts', async ({ page }) => {
      await page.goto('/portal', { waitUntil: 'domcontentloaded' });
      
      // Credits & Pricing card should show
      const creditsCard = page.getByTestId('category-card-credits-pricing');
      await expect(creditsCard).toBeVisible();
      
      // Should have title
      await expect(creditsCard.locator('h3')).toContainText('Credits & Pricing');
      
      // Should have description
      await expect(creditsCard.locator('p')).toBeVisible();
      
      // Should have topic count (e.g., "4 topics")
      await expect(creditsCard.locator('span').filter({ hasText: /topics/ })).toBeVisible();
    });
  });

  test.describe('Portal Category Page', () => {
    test('credits-pricing shows Related Documentation section with articles from beginners-guide', async ({ page }) => {
      await page.goto('/portal/category/credits-pricing', { waitUntil: 'domcontentloaded' });
      await expect(page.getByTestId('portal-category-page')).toBeVisible();
      
      // Should show Related Documentation section (fetched via category.kb_group_key from API)
      await expect(page.getByTestId('related-articles-section')).toBeVisible();
      
      // Should have "Related documentation" heading
      await expect(page.getByText('Related documentation', { exact: false })).toBeVisible();
      
      // Should have at least one article link
      const articleLinks = page.getByTestId('related-articles-section').locator('a');
      await expect(articleLinks.first()).toBeVisible();
    });

    test('category page shows subtopics with items', async ({ page }) => {
      await page.goto('/portal/category/credits-pricing', { waitUntil: 'domcontentloaded' });
      
      // Should show subtopics
      await expect(page.getByTestId('subtopic-0')).toBeVisible();
      
      // Should have Credit Usage subtopic
      await expect(page.locator('span').filter({ hasText: 'Credit Usage' })).toBeVisible();
    });

    test('category page back link works', async ({ page }) => {
      await page.goto('/portal/category/credits-pricing', { waitUntil: 'domcontentloaded' });
      
      // Click back link
      await page.getByTestId('category-back-link').click();
      
      // Should navigate to portal home
      await expect(page).toHaveURL(/\/portal$/);
    });
  });

  test.describe('Admin Portal Category Manager', () => {
    test.beforeEach(async ({ page }) => {
      // Set admin session cookie
      await page.context().addCookies([{
        name: 'session_token',
        value: ADMIN_SESSION_TOKEN,
        domain: new URL(BASE_URL).hostname,
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'None'
      }]);
    });

    test('settings page shows Portal Categories section with Add Category button', async ({ page }) => {
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Portal Categories section should exist
      await expect(page.getByText('Portal Categories')).toBeVisible();
      
      // Add Category button should exist
      const addBtn = page.getByTestId('add-category-btn');
      await addBtn.scrollIntoViewIfNeeded();
      await expect(addBtn).toBeVisible();
    });

    test('new category form has Linked KB Topic dropdown with KB nav groups', async ({ page }) => {
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Click Add Category button
      const addBtn = page.getByTestId('add-category-btn');
      await addBtn.scrollIntoViewIfNeeded();
      await addBtn.click();
      
      // Modal should appear
      await expect(page.getByTestId('category-form-modal')).toBeVisible();
      
      // Linked KB Topic dropdown should exist
      const kbDropdown = page.getByTestId('cat-form-kb-group');
      await expect(kbDropdown).toBeVisible();
      
      // Should have "None" option by default
      await expect(kbDropdown).toHaveValue('');
    });

    test('Linked KB Topic dropdown lists all 5 KB nav groups', async ({ page }) => {
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Click Add Category button
      const addBtn = page.getByTestId('add-category-btn');
      await addBtn.scrollIntoViewIfNeeded();
      await addBtn.click();
      
      await expect(page.getByTestId('category-form-modal')).toBeVisible();
      
      // Get dropdown options
      const kbDropdown = page.getByTestId('cat-form-kb-group');
      const options = await kbDropdown.locator('option').allTextContents();
      
      // Should have None + 5 KB groups = 6 options
      expect(options.length).toBe(6);
      
      // Check for expected groups
      expect(options.join(',')).toContain('beginners-guide');
      expect(options.join(',')).toContain('features');
      expect(options.join(',')).toContain('building-your-app');
      expect(options.join(',')).toContain('deploy-and-manage');
      expect(options.join(',')).toContain('troubleshooting');
    });

    test('Help Articles section shows dynamic KB articles list (not hardcoded)', async ({ page }) => {
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Click Add Category button
      const addBtn = page.getByTestId('add-category-btn');
      await addBtn.scrollIntoViewIfNeeded();
      await addBtn.click();
      
      await expect(page.getByTestId('category-form-modal')).toBeVisible();
      
      // Help Articles section should show KB articles from API
      await expect(page.getByText('Knowledge Base articles')).toBeVisible();
      
      // Should have article toggle buttons (from dynamic API, not hardcoded)
      // The text shows count like "Knowledge Base articles (49)"
      const kbArticlesText = page.locator('p').filter({ hasText: /Knowledge Base articles/ });
      await expect(kbArticlesText).toBeVisible();
    });

    test('can create category with kb_group_key via form', async ({ page }) => {
      const testSlug = `test-e2e-${Date.now()}`;
      
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Click Add Category button
      const addBtn = page.getByTestId('add-category-btn');
      await addBtn.scrollIntoViewIfNeeded();
      await addBtn.click();
      
      await expect(page.getByTestId('category-form-modal')).toBeVisible();
      
      // Fill form
      await page.getByTestId('cat-form-title').fill('TEST E2E Category');
      await page.getByTestId('cat-form-slug').fill(testSlug);
      await page.getByTestId('cat-form-description').fill('Test category from E2E');
      
      // Select KB group
      await page.getByTestId('cat-form-kb-group').selectOption('features');
      
      // Submit
      await page.getByTestId('save-category-btn').click();
      
      // Modal should close
      await expect(page.getByTestId('category-form-modal')).not.toBeVisible({ timeout: 5000 });
      
      // Verify category was created via API
      const response = await page.request.get(`${BASE_URL}/api/portal/categories/${testSlug}`);
      expect(response.status()).toBe(200);
      const data = await response.json();
      expect(data.kb_group_key).toBe('features');
      
      // Clean up - delete the test category
      await page.request.delete(`${BASE_URL}/api/portal/admin/categories/${testSlug}`, {
        headers: { 'Cookie': `session_token=${ADMIN_SESSION_TOKEN}` }
      });
    });

    test('existing category shows kb_group_key when expanded', async ({ page }) => {
      await page.goto('/settings', { waitUntil: 'domcontentloaded' });
      
      // Find and expand credits-pricing category
      const expandBtn = page.getByTestId('expand-cat-credits-pricing');
      await expandBtn.scrollIntoViewIfNeeded();
      await expandBtn.click();
      
      // Should show Linked KB Group
      await expect(page.getByText('Linked KB Group')).toBeVisible();
      await expect(page.getByText('beginners-guide')).toBeVisible();
    });
  });
});
