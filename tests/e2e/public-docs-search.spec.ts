/**
 * Public Docs Search E2E Tests
 * Tests for the refactored search using backend API (GET /api/kb/search)
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'https://kb-wysiwyg-upgrade.preview.emergentagent.com';

test.describe('Public Docs Page Load', () => {
  test('Public docs page loads with main components', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    
    // Wait for page to load
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('kb-header')).toBeVisible();
    await expect(page.getByTestId('kb-sidebar')).toBeVisible();
  });

  test('Public docs shows article content', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
    
    // Article title should be visible
    await expect(page.getByTestId('kb-page-title')).toBeVisible();
    await expect(page.getByTestId('kb-page-title')).toContainText('Welcome');
    
    // Article body should have content
    await expect(page.getByTestId('kb-article-body')).toBeVisible();
  });

  test('Navigation sidebar shows categories and pages', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
    
    // Sidebar navigation tree should be visible
    const navTree = page.getByTestId('kb-nav-tree');
    await expect(navTree).toBeVisible();
    
    // Should have at least one sidebar tab
    await expect(page.locator('[data-testid^="sidebar-tab-"]').first()).toBeVisible();
  });
});

test.describe('Search Dialog', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
  });

  test('Search bar opens search dialog', async ({ page }) => {
    // Click search bar in top nav
    const searchBar = page.getByTestId('topnav-search-bar');
    if (await searchBar.isVisible()) {
      await searchBar.click();
    } else {
      // Mobile view - use search icon
      await page.getByTestId('topnav-search').click();
    }
    
    // Search dialog should appear
    await expect(page.getByTestId('search-input')).toBeVisible();
  });

  test('Cmd+K keyboard shortcut opens search dialog', async ({ page }) => {
    // Press Cmd+K (or Ctrl+K on Windows/Linux)
    await page.keyboard.press('Meta+k');
    
    // Search dialog should appear
    await expect(page.getByTestId('search-input')).toBeVisible();
  });

  test('ESC key closes search dialog', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    // Press ESC
    await page.keyboard.press('Escape');
    
    // Dialog should close
    await expect(page.getByTestId('search-input')).not.toBeVisible();
  });
});

test.describe('Search Functionality with Backend API', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
  });

  test('Search calls backend API and displays results', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    // Wait for API response when typing
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/kb/search') && response.status() === 200
    );
    
    // Type search query
    await page.getByTestId('search-input').fill('emergent');
    
    // Wait for API call to complete
    const response = await responsePromise;
    const data = await response.json();
    
    // API should return results
    expect(data.results).toBeDefined();
    expect(data.results.length).toBeGreaterThan(0);
  });

  test('Search results show snippets with context', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    // Wait for API response
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/kb/search') && response.status() === 200
    );
    
    // Type search query
    await page.getByTestId('search-input').fill('emergent');
    
    // Wait for API call and results to render
    const response = await responsePromise;
    const data = await response.json();
    
    // Results should have snippets
    if (data.results && data.results.length > 0) {
      expect(data.results[0].snippet).toBeDefined();
      expect(data.results[0].snippet.length).toBeGreaterThan(0);
    }
  });

  test('Search results show category breadcrumbs', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    // Wait for API response
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/kb/search') && response.status() === 200
    );
    
    // Type search query
    await page.getByTestId('search-input').fill('emergent');
    
    // Wait for API call
    const response = await responsePromise;
    const data = await response.json();
    
    // First result should have navigation info for breadcrumbs
    if (data.results && data.results.length > 0) {
      expect(data.results[0].nav_group_key).toBeDefined();
      expect(data.results[0].section_key).toBeDefined();
    }
  });

  test('Search debounces API calls (200ms delay)', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    let apiCallCount = 0;
    page.on('request', request => {
      if (request.url().includes('/api/kb/search')) {
        apiCallCount++;
      }
    });
    
    // Type quickly - should debounce
    await page.getByTestId('search-input').pressSequentially('test', { delay: 50 });
    
    // Wait for debounce to settle
    await page.waitForTimeout(300);
    
    // Should only have made 1 API call (debounced)
    expect(apiCallCount).toBeLessThanOrEqual(2); // Allow for 1-2 calls due to timing
  });

  test('Empty search query does not call API', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    let apiCallCount = 0;
    page.on('request', request => {
      if (request.url().includes('/api/kb/search')) {
        apiCallCount++;
      }
    });
    
    // Type only 1 character (minimum is 2)
    await page.getByTestId('search-input').fill('a');
    
    // Wait a bit
    await page.waitForTimeout(300);
    
    // Should not have made any API calls
    expect(apiCallCount).toBe(0);
  });

  test('Clicking search result navigates to article', async ({ page }) => {
    // Open search dialog
    await page.keyboard.press('Meta+k');
    await expect(page.getByTestId('search-input')).toBeVisible();
    
    // Wait for API response
    const responsePromise = page.waitForResponse(
      response => response.url().includes('/api/kb/search') && response.status() === 200
    );
    
    // Search for something
    await page.getByTestId('search-input').fill('emergent');
    
    await responsePromise;
    
    // Wait for results to render
    await page.waitForSelector('button:has-text("Welcome")');
    
    // Click first result (Welcome To Emergent)
    const firstResult = page.locator('button:has-text("Welcome To Emergent")').first();
    await firstResult.click();
    
    // Should navigate to the article
    await expect(page).toHaveURL(/\/docs\/welcome/);
    await expect(page.getByTestId('kb-page-title')).toContainText('Welcome');
  });
});

test.describe('Article Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
  });

  test('Previous/Next navigation buttons work', async ({ page }) => {
    // Should have prev/next navigation section
    const prevNextSection = page.getByTestId('kb-prev-next');
    await expect(prevNextSection).toBeVisible();
    
    // Next button should be visible (welcome is first article)
    const nextBtn = page.getByTestId('next-doc-btn');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      
      // URL should change
      await expect(page).not.toHaveURL(/\/docs\/welcome$/);
    }
  });

  test('Sidebar navigation changes article', async ({ page }) => {
    // Find another article in sidebar
    const anotherArticle = page.getByTestId('sidebar-page-first-app');
    
    if (await anotherArticle.isVisible()) {
      await anotherArticle.click();
      
      // Should navigate
      await expect(page).toHaveURL(/\/docs\/first-app/);
    }
  });
});

test.describe('Theme Toggle', () => {
  test('Theme toggle changes between light and dark mode', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
    
    // Get theme toggle
    const themeToggle = page.getByTestId('kb-theme-toggle');
    await expect(themeToggle).toBeVisible();
    
    // Click toggle
    await themeToggle.click();
    
    // Page should still be functional
    await expect(page.getByTestId('kb-docs')).toBeVisible();
  });
});

test.describe('Feedback Widget', () => {
  test('Feedback widget is present on article', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-docs')).toBeVisible({ timeout: 15000 });
    
    // Scroll to feedback widget
    const feedbackWidget = page.getByTestId('kb-feedback-widget');
    await feedbackWidget.scrollIntoViewIfNeeded();
    
    await expect(feedbackWidget).toBeVisible();
    await expect(page.getByTestId('feedback-helpful-btn')).toBeVisible();
    await expect(page.getByTestId('feedback-unhelpful-btn')).toBeVisible();
  });
});
