/**
 * KB Editor Visual Edit Mode - Click Tests
 * Tests bug fix: Clicking on cards/iframes should not produce RangeError
 * Bug: "Selection passed to setSelection must point at the current document"
 * Fix: Added stopEvent to ReactNodeViewRenderer for atom nodes (ColumnCardNode and IframeEmbed)
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://docs-sync-test.preview.emergentagent.com';
const SESSION_TOKEN = 'qa_test_admin_session_token_2026';

async function authenticateKBEditor(page: Page) {
  await page.context().addCookies([{
    name: 'session_token',
    value: SESSION_TOKEN,
    domain: 'kb-wysiwyg-upgrade.preview.emergentagent.com',
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'None'
  }]);
}

test.describe('Visual Editor - Card and Iframe Click Handling', () => {
  let consoleErrors: string[] = [];
  
  test.beforeEach(async ({ page }) => {
    // Reset console errors tracking
    consoleErrors = [];
    
    // Capture console errors, specifically looking for RangeError/Selection errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    page.on('pageerror', error => {
      consoleErrors.push(error.message);
    });
    
    await authenticateKBEditor(page);
  });

  test('Standalone iframe embed is visible and clickable without errors', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    // Wait for Visual Edit mode (default mode)
    await expect(page.getByText('Visual Edit')).toBeVisible();
    
    // Wait for editor to load content
    await expect(page.getByTestId('rich-text-editor')).toBeVisible();
    
    // Look for standalone iframe embed
    const iframeEmbed = page.getByTestId('iframe-embed').first();
    if (await iframeEmbed.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Click on the iframe embed - should NOT produce RangeError
      await iframeEmbed.click({ force: true });
      
      // Check no RangeError in console
      const rangeErrors = consoleErrors.filter(e => 
        e.includes('RangeError') || 
        e.includes('Selection passed to setSelection')
      );
      expect(rangeErrors).toHaveLength(0);
    }
  });

  test('Iframe embed edit button opens popup without errors', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('rich-text-editor')).toBeVisible();
    
    // Find iframe embed and hover to show edit button
    const iframeEmbed = page.getByTestId('iframe-embed').first();
    if (await iframeEmbed.isVisible({ timeout: 5000 }).catch(() => false)) {
      await iframeEmbed.hover();
      
      // Click edit button
      const editBtn = page.getByTestId('iframe-embed-edit-btn').first();
      if (await editBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await editBtn.click();
        
        // Edit popup should appear
        await expect(page.getByTestId('iframe-embed-popup')).toBeVisible();
        
        // No errors should occur
        const rangeErrors = consoleErrors.filter(e => 
          e.includes('RangeError') || 
          e.includes('Selection passed to setSelection')
        );
        expect(rangeErrors).toHaveLength(0);
      }
    }
  });

  test('Column card is clickable and opens edit popup without errors', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('rich-text-editor')).toBeVisible();
    
    // Look for column cards (inside columns-block)
    const columnsBlock = page.getByTestId('columns-block').first();
    if (await columnsBlock.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Find a column card
      const columnCard = page.getByTestId('column-card').first();
      if (await columnCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Click on the card visual
        const cardVisual = columnCard.getByTestId('card-visual');
        await cardVisual.click({ force: true });
        
        // Card settings popup should appear
        await expect(page.getByTestId('card-settings-popup')).toBeVisible({ timeout: 5000 });
        
        // No RangeError should occur
        const rangeErrors = consoleErrors.filter(e => 
          e.includes('RangeError') || 
          e.includes('Selection passed to setSelection')
        );
        expect(rangeErrors).toHaveLength(0);
      }
    }
  });

  test('Iframe card within columns is clickable without errors', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('rich-text-editor')).toBeVisible();
    
    // Look for iframe-type cards within columns
    const iframeCard = page.getByTestId('column-card-iframe').first();
    if (await iframeCard.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Hover to show edit button
      await iframeCard.hover();
      
      // Click the edit button
      const editBtn = page.getByTestId('iframe-edit-btn').first();
      if (await editBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await editBtn.click();
        
        // Edit popup should appear
        await expect(page.getByTestId('iframe-settings-popup')).toBeVisible();
        
        // No errors
        const rangeErrors = consoleErrors.filter(e => 
          e.includes('RangeError') || 
          e.includes('Selection passed to setSelection')
        );
        expect(rangeErrors).toHaveLength(0);
      }
    }
  });
});

test.describe('Public Docs Page - Cards and Iframes Rendering', () => {
  test('Welcome page renders standalone iframe correctly', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('doc-content')).toBeVisible({ timeout: 15000 });
    
    // Check for YouTube embed (standalone iframe)
    const youtubeEmbed = page.getByTestId('youtube-embed').first();
    if (await youtubeEmbed.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Verify iframe is rendered with correct src
      const iframe = youtubeEmbed.locator('iframe');
      await expect(iframe).toBeVisible();
      const src = await iframe.getAttribute('src');
      expect(src).toContain('youtube.com/embed');
    }
  });

  test('Welcome page renders column cards correctly', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('doc-content')).toBeVisible({ timeout: 15000 });
    
    // Check for columns component
    const columns = page.getByTestId('columns').first();
    if (await columns.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Check for cards within columns
      const cards = columns.getByTestId('card');
      const cardCount = await cards.count();
      expect(cardCount).toBeGreaterThan(0);
    }
  });

  test('Cards display title, description, and icon', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('doc-content')).toBeVisible({ timeout: 15000 });
    
    // Find first card and verify structure
    const card = page.getByTestId('card').first();
    if (await card.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Card should have a heading (title)
      const heading = card.locator('h4');
      await expect(heading).toBeVisible();
      
      // Card should have description text
      const hasText = await card.textContent();
      expect(hasText?.length).toBeGreaterThan(0);
    }
  });
});

test.describe('Portal Help Topics API', () => {
  test('GET /api/portal/help-topics returns topics', async ({ page }) => {
    const response = await page.request.get('/api/portal/help-topics');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.topics).toBeDefined();
    expect(data.topics.length).toBeGreaterThan(0);
    
    // Check topic structure
    const firstTopic = data.topics[0];
    expect(firstTopic.key).toBeDefined();
    expect(firstTopic.label).toBeDefined();
    expect(firstTopic.article_count).toBeGreaterThanOrEqual(0);
  });
});
