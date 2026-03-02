import { test, expect } from '@playwright/test';

test.describe('Portal Help Topics - KB-derived Documentation', () => {
  
  test.beforeEach(async ({ page }) => {
    // Remove any overlay badges that might block interactions
    await page.addInitScript(() => {
      const observer = new MutationObserver(() => {
        const badge = document.querySelector('[class*="emergent-badge"], [id*="emergent"]');
        if (badge) badge.remove();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    });
  });

  test('Portal home page loads and shows hero title', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-home')).toBeVisible();
    await expect(page.getByTestId('portal-hero-title')).toHaveText('How can we help?');
  });

  test('Portal home page shows Browse our documentation section', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    // Wait for help topics to load
    await expect(page.getByTestId('docs-topics-section')).toBeVisible({ timeout: 10000 });
    
    // Check section header
    await expect(page.getByText('Browse our documentation')).toBeVisible();
    
    // Check at least one topic card is visible
    const topicCard = page.locator('[data-testid^="docs-topic-card-"]').first();
    await expect(topicCard).toBeVisible();
  });

  test('KB topic cards display correct structure', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('docs-topics-section')).toBeVisible({ timeout: 10000 });
    
    // Check beginners-guide topic card specifically
    const beginnersCard = page.getByTestId('docs-topic-card-beginners-guide');
    await expect(beginnersCard).toBeVisible();
    
    // Card should show label and article count
    await expect(beginnersCard).toContainText("Beginner's Guide");
    await expect(beginnersCard).toContainText('articles');
  });

  test('Clicking KB topic card navigates to /portal/topic/{key}', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('docs-topics-section')).toBeVisible({ timeout: 10000 });
    
    // Click the beginners-guide topic card
    await page.getByTestId('docs-topic-card-beginners-guide').click();
    
    // Should navigate to the topic page
    await expect(page).toHaveURL(/\/portal\/topic\/beginners-guide/);
    await expect(page.getByTestId('help-topic-page')).toBeVisible();
  });

  test('PortalHelpTopic page displays topic details', async ({ page }) => {
    await page.goto('/portal/topic/beginners-guide', { waitUntil: 'domcontentloaded' });
    
    // Wait for topic to load
    await expect(page.getByTestId('help-topic-page')).toBeVisible({ timeout: 10000 });
    
    // Check title
    await expect(page.getByTestId('help-topic-title')).toContainText("Beginner's Guide");
    
    // Check back link
    await expect(page.getByTestId('help-topic-back')).toBeVisible();
  });

  test('PortalHelpTopic page shows sections with articles', async ({ page }) => {
    await page.goto('/portal/topic/beginners-guide', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('help-topic-page')).toBeVisible({ timeout: 10000 });
    
    // Check for sections
    const introSection = page.getByTestId('help-section-introduction');
    await expect(introSection).toBeVisible();
    
    // Check for article links within sections
    const welcomeArticle = page.getByTestId('help-article-welcome');
    await expect(welcomeArticle).toBeVisible();
    await expect(welcomeArticle).toContainText('Welcome To Emergent');
  });

  test('PortalHelpTopic article links open in new tab', async ({ page }) => {
    await page.goto('/portal/topic/beginners-guide', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('help-topic-page')).toBeVisible({ timeout: 10000 });
    
    // Check article link has target="_blank"
    const welcomeArticle = page.getByTestId('help-article-welcome');
    await expect(welcomeArticle).toHaveAttribute('target', '_blank');
    await expect(welcomeArticle).toHaveAttribute('href', '/docs/welcome');
  });

  test('PortalHelpTopic page shows submit ticket CTA', async ({ page }) => {
    await page.goto('/portal/topic/features', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('help-topic-page')).toBeVisible({ timeout: 10000 });
    
    // Check submit ticket button
    await expect(page.getByTestId('help-topic-submit-btn')).toBeVisible();
    await expect(page.getByTestId('help-topic-submit-btn')).toContainText('Submit a ticket');
  });

  test('PortalHelpTopic 404 page for nonexistent topic', async ({ page }) => {
    await page.goto('/portal/topic/nonexistent-topic-xyz', { waitUntil: 'domcontentloaded' });
    
    // Should show not found message
    await expect(page.getByTestId('help-topic-not-found')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Topic not found')).toBeVisible();
  });

  test('PortalHelpTopic back link navigates to portal home', async ({ page }) => {
    await page.goto('/portal/topic/features', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('help-topic-page')).toBeVisible({ timeout: 10000 });
    
    // Click back link
    await page.getByTestId('help-topic-back').click();
    
    // Should navigate back to portal home
    await expect(page).toHaveURL(/\/portal$/);
    await expect(page.getByTestId('portal-home')).toBeVisible();
  });
});

test.describe('Portal Categories - Existing Functionality', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const observer = new MutationObserver(() => {
        const badge = document.querySelector('[class*="emergent-badge"], [id*="emergent"]');
        if (badge) badge.remove();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    });
  });

  test('Portal home page shows ticket categories section', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('categories-section')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Submit a ticket by topic')).toBeVisible();
  });

  test('Category cards are displayed', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('categories-section')).toBeVisible({ timeout: 10000 });
    
    // Check features category card
    const featuresCard = page.getByTestId('category-card-features');
    await expect(featuresCard).toBeVisible();
    await expect(featuresCard).toContainText('Features');
  });

  test('Clicking category card navigates to category page', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('categories-section')).toBeVisible({ timeout: 10000 });
    
    await page.getByTestId('category-card-features').click();
    
    await expect(page).toHaveURL(/\/portal\/category\/features/);
    await expect(page.getByTestId('portal-category-page')).toBeVisible();
  });

  test('PortalCategory page shows Related Documentation section', async ({ page }) => {
    // Use deployments category which maps to deploy-and-manage KB group
    await page.goto('/portal/category/deployments', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-category-page')).toBeVisible({ timeout: 10000 });
    
    // Check for related articles section
    const relatedSection = page.getByTestId('related-articles-section');
    await expect(relatedSection).toBeVisible();
    await expect(relatedSection).toContainText('Related documentation');
  });

  test('PortalCategory related articles are clickable', async ({ page }) => {
    await page.goto('/portal/category/deployments', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-category-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('related-articles-section')).toBeVisible({ timeout: 5000 });
    
    // Check that related article links exist and have correct attributes
    const articleLink = page.locator('[data-testid^="related-article-"]').first();
    await expect(articleLink).toBeVisible();
    await expect(articleLink).toHaveAttribute('target', '_blank');
  });

  test('PortalCategory page shows subtopics', async ({ page }) => {
    await page.goto('/portal/category/features', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-category-page')).toBeVisible({ timeout: 10000 });
    
    // Check subtopics are displayed
    const firstSubtopic = page.getByTestId('subtopic-0');
    await expect(firstSubtopic).toBeVisible();
  });

  test('PortalCategory back link navigates to portal home', async ({ page }) => {
    await page.goto('/portal/category/features', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-category-page')).toBeVisible({ timeout: 10000 });
    
    await page.getByTestId('category-back-link').click();
    
    await expect(page).toHaveURL(/\/portal$/);
    await expect(page.getByTestId('portal-home')).toBeVisible();
  });

  test('PortalCategory submit button navigates to submit page', async ({ page }) => {
    await page.goto('/portal/category/features', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('portal-category-page')).toBeVisible({ timeout: 10000 });
    
    await page.getByTestId('category-submit-btn').click();
    
    await expect(page).toHaveURL(/\/portal\/submit.*category=features/);
  });

  test('Portal search filters categories', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('categories-section')).toBeVisible({ timeout: 10000 });
    
    // Type in search
    await page.getByTestId('portal-search-input').fill('deployment');
    
    // Should filter to show only deployments category
    await expect(page.getByTestId('category-card-deployments')).toBeVisible();
  });
});

test.describe('Portal Contact Cards', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const observer = new MutationObserver(() => {
        const badge = document.querySelector('[class*="emergent-badge"], [id*="emergent"]');
        if (badge) badge.remove();
      });
      observer.observe(document.body, { childList: true, subtree: true });
    });
  });

  test('Product help card is clickable', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await expect(page.getByTestId('product-help-card')).toBeVisible();
    await expect(page.getByTestId('product-help-card')).toContainText('Product help');
  });

  test('Partner programs card opens inquiry modal', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await page.getByTestId('partner-card').click();
    
    await expect(page.getByTestId('modal-overlay')).toBeVisible();
    await expect(page.getByText('Enquire about partner programs')).toBeVisible();
  });

  test('Sales card opens inquiry modal', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await page.getByTestId('sales-card').click();
    
    await expect(page.getByTestId('modal-overlay')).toBeVisible();
    await expect(page.getByText('Talk to sales')).toBeVisible();
  });

  test('Emergency card navigates to submit page', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await page.getByTestId('emergency-card').click();
    
    await expect(page).toHaveURL(/\/portal\/submit.*priority=emergency/);
  });

  test('Submit ticket CTA navigates to submit page', async ({ page }) => {
    await page.goto('/portal', { waitUntil: 'domcontentloaded' });
    
    await page.getByTestId('portal-submit-cta').click();
    
    await expect(page).toHaveURL(/\/portal\/submit/);
  });
});
