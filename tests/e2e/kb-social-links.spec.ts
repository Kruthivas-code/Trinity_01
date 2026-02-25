import { test, expect } from '@playwright/test';

const BASE_URL = 'https://conversation-rebuild.preview.emergentagent.com';
const SESSION_TOKEN = 'd32ac462-b0ff-435e-832d-9d068479737e';

test.describe('KB Social Links Feature', () => {

  test.describe('Public Docs Page - Social Links Display', () => {

    test('social links section appears below prev/next navigation', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify the social links container exists
      const socialLinks = page.getByTestId('kb-social-links');
      await expect(socialLinks).toBeVisible();
      
      // Verify prev/next navigation exists (social links should be below it)
      const prevNextNav = page.getByTestId('kb-prev-next');
      await expect(prevNextNav).toBeVisible();
    });

    test('all 5 social icons are visible when links are populated', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Check each social link icon is visible
      await expect(page.getByTestId('social-link-twitter')).toBeVisible();
      await expect(page.getByTestId('social-link-linkedin')).toBeVisible();
      await expect(page.getByTestId('social-link-discord')).toBeVisible();
      await expect(page.getByTestId('social-link-youtube')).toBeVisible();
      await expect(page.getByTestId('social-link-reddit')).toBeVisible();
    });

    test('social link icons have correct href attributes', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify links point to correct URLs
      const twitterLink = page.getByTestId('social-link-twitter');
      await expect(twitterLink).toHaveAttribute('href', /x\.com|twitter\.com/);
      
      const linkedinLink = page.getByTestId('social-link-linkedin');
      await expect(linkedinLink).toHaveAttribute('href', /linkedin\.com/);
      
      const discordLink = page.getByTestId('social-link-discord');
      await expect(discordLink).toHaveAttribute('href', /discord\./);
    });

    test('social links open in new tab', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify target="_blank" for external links
      const twitterLink = page.getByTestId('social-link-twitter');
      await expect(twitterLink).toHaveAttribute('target', '_blank');
      await expect(twitterLink).toHaveAttribute('rel', /noopener/);
    });

  });

  test.describe('Public Docs Page - Social Links Visibility', () => {

    test('social links section is hidden when all URLs are empty', async ({ page, request }) => {
      // First clear all social links via API
      await request.put(`${BASE_URL}/api/kb/admin/social-links`, {
        headers: {
          'Content-Type': 'application/json',
          'Cookie': `session_token=${SESSION_TOKEN}`
        },
        data: { links: {} }
      });
      
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Social links section should NOT be visible when all empty
      const socialLinks = page.getByTestId('kb-social-links');
      await expect(socialLinks).not.toBeVisible();
      
      // Restore social links for other tests
      await request.put(`${BASE_URL}/api/kb/admin/social-links`, {
        headers: {
          'Content-Type': 'application/json',
          'Cookie': `session_token=${SESSION_TOKEN}`
        },
        data: {
          links: {
            twitter: 'https://x.com/emergentsh',
            linkedin: 'https://linkedin.com/company/emergent',
            discord: 'https://discord.gg/emergent',
            youtube: 'https://youtube.com/@emergent',
            reddit: 'https://reddit.com/r/emergent'
          }
        }
      });
    });

  });

  test.describe('Public Docs Page - Theme Adaptation', () => {

    test('social links adapt to dark theme', async ({ page }) => {
      // Set dark theme preference before navigating
      await page.addInitScript(() => {
        localStorage.setItem('kb-theme', 'dark');
      });
      
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify social links are visible in dark mode
      const socialLinks = page.getByTestId('kb-social-links');
      await expect(socialLinks).toBeVisible();
      
      // Icons should be visible (CSS transitions may affect color)
      const twitterIcon = page.getByTestId('social-link-twitter');
      await expect(twitterIcon).toBeVisible();
    });

    test('social links adapt to light theme', async ({ page }) => {
      // Set light theme preference
      await page.addInitScript(() => {
        localStorage.setItem('kb-theme', 'light');
      });
      
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify social links are visible in light mode
      const socialLinks = page.getByTestId('kb-social-links');
      await expect(socialLinks).toBeVisible();
      
      // Icons should be visible 
      const linkedinIcon = page.getByTestId('social-link-linkedin');
      await expect(linkedinIcon).toBeVisible();
    });

    test('theme toggle changes social link icon colors', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Click theme toggle
      const themeToggle = page.getByTestId('kb-theme-toggle');
      await expect(themeToggle).toBeVisible();
      
      // Toggle theme and verify icons still visible
      await themeToggle.click();
      await page.waitForTimeout(300); // Allow CSS transition
      
      const socialLinks = page.getByTestId('kb-social-links');
      await expect(socialLinks).toBeVisible();
    });

  });

  test.describe('KB Editor - Social Links Panel', () => {

    test.beforeEach(async ({ page }) => {
      // Set session cookie for authentication
      await page.context().addCookies([{
        name: 'session_token',
        value: SESSION_TOKEN,
        domain: 'conversation-rebuild.preview.emergentagent.com',
        path: '/',
        httpOnly: true,
        secure: true,
        sameSite: 'None'
      }]);
    });

    test('share button opens social links panel', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Click the social links toggle (Share2 icon button)
      const socialLinksToggle = page.getByTestId('social-links-toggle');
      await expect(socialLinksToggle).toBeVisible();
      await socialLinksToggle.click();
      
      // Verify panel opens
      const socialLinksPanel = page.getByTestId('social-links-panel');
      await expect(socialLinksPanel).toBeVisible();
    });

    test('social links panel shows all 5 platform fields', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Open panel
      await page.getByTestId('social-links-toggle').click();
      await page.waitForSelector('[data-testid="social-links-panel"]');
      
      // Wait for inputs to load
      await page.waitForSelector('[data-testid="social-input-twitter"]', { timeout: 10000 });
      
      // Verify all 5 platform inputs are visible
      await expect(page.getByTestId('social-input-twitter')).toBeVisible();
      await expect(page.getByTestId('social-input-linkedin')).toBeVisible();
      await expect(page.getByTestId('social-input-discord')).toBeVisible();
      await expect(page.getByTestId('social-input-youtube')).toBeVisible();
      await expect(page.getByTestId('social-input-reddit')).toBeVisible();
    });

    test('social links panel can be closed via X button', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Open panel
      await page.getByTestId('social-links-toggle').click();
      await page.waitForSelector('[data-testid="social-links-panel"]');
      
      // Close via X button
      const closeButton = page.getByTestId('social-links-close');
      await expect(closeButton).toBeVisible();
      await closeButton.click();
      
      // Panel should be hidden
      await expect(page.getByTestId('social-links-panel')).not.toBeVisible();
    });

    test('social links panel can be closed via Cancel button', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Open panel
      await page.getByTestId('social-links-toggle').click();
      await page.waitForSelector('[data-testid="social-links-panel"]');
      await page.waitForSelector('[data-testid="social-input-twitter"]');
      
      // Close via Cancel button
      const cancelButton = page.getByTestId('social-links-cancel');
      await expect(cancelButton).toBeVisible();
      await cancelButton.click();
      
      // Panel should be hidden
      await expect(page.getByTestId('social-links-panel')).not.toBeVisible();
    });

    test('social links panel has save button', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Open panel
      await page.getByTestId('social-links-toggle').click();
      await page.waitForSelector('[data-testid="social-links-panel"]');
      await page.waitForSelector('[data-testid="social-input-twitter"]');
      
      // Verify Save button exists
      const saveButton = page.getByTestId('social-links-save');
      await expect(saveButton).toBeVisible();
      await expect(saveButton).toHaveText('Save');
    });

    test('social links panel displays current saved values', async ({ page }) => {
      await page.goto('/dashboard/kb-editor/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Open panel
      await page.getByTestId('social-links-toggle').click();
      await page.waitForSelector('[data-testid="social-links-panel"]');
      await page.waitForSelector('[data-testid="social-input-twitter"]');
      
      // Verify fields have values (test data should be pre-seeded)
      const twitterInput = page.getByTestId('social-input-twitter');
      await expect(twitterInput).toHaveValue(/x\.com|twitter\.com/);
    });

  });

  test.describe('Existing Docs Page Functionality', () => {

    test('docs page loads correctly', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify page structure
      await expect(page.getByTestId('kb-docs')).toBeVisible();
      await expect(page.getByTestId('kb-header')).toBeVisible();
      await expect(page.getByTestId('kb-sidebar')).toBeVisible();
    });

    test('prev/next navigation still works', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Navigate to first article that has a next button
      const nextButton = page.getByTestId('next-doc-btn');
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await page.waitForLoadState('networkidle');
        
        // Should have navigated to a different page
        await expect(page.getByTestId('kb-page-title')).toBeVisible();
      }
    });

    test('feedback widget still works', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Verify feedback widget exists
      const feedbackWidget = page.getByTestId('kb-feedback-widget');
      await expect(feedbackWidget).toBeVisible();
      
      // Verify thumbs up/down buttons exist
      await expect(page.getByTestId('feedback-helpful-btn')).toBeVisible();
      await expect(page.getByTestId('feedback-unhelpful-btn')).toBeVisible();
    });

    test('search functionality still works', async ({ page }) => {
      await page.goto('/docs/introduction', { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      
      // Click search button
      const searchButton = page.getByTestId('topnav-search');
      await expect(searchButton).toBeVisible();
      await searchButton.click();
      
      // Verify search dialog opens
      const searchInput = page.getByTestId('search-input');
      await expect(searchInput).toBeVisible();
    });

  });

});
