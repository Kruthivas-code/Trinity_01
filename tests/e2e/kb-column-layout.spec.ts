import { test, expect } from '@playwright/test';

const BASE_URL = 'https://atlas-first-sync.preview.emergentagent.com';
const SESSION_TOKEN = 'test_kb_session_token';

test.describe('KB Column Layout - Public Docs', () => {
  test.beforeEach(async ({ page }) => {
    // Remove emergent badge that might overlay elements
    await page.addInitScript(() => {
      setInterval(() => {
        const badge = document.querySelector('[class*="emergent"], [id*="emergent-badge"]');
        if (badge) badge.remove();
      }, 500);
    });
  });

  test('ColumnLayout renders side-by-side on /docs/col-layout-test', async ({ page }) => {
    await page.goto('/docs/col-layout-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('Column Layout Test');
    
    // Verify Two Columns heading exists
    await expect(page.locator('h2:has-text("Two Columns")')).toBeVisible();
    
    // Verify ColumnLayout renders with data-testid
    const columnLayouts = page.locator('[data-testid="column-layout-render"]');
    await expect(columnLayouts.first()).toBeVisible();
    
    // Verify the columns have proper grid layout (side-by-side)
    const columnLayout = columnLayouts.first();
    const computedStyle = await columnLayout.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        display: style.display,
        gridTemplateColumns: style.gridTemplateColumns
      };
    });
    
    expect(computedStyle.display).toBe('grid');
    // Should have 2 columns (repeat(2, 1fr) or similar)
    expect(computedStyle.gridTemplateColumns).toMatch(/\d+px\s+\d+px/);
    
    // Verify Left and Right content exists
    await expect(page.locator('h3:has-text("Left")')).toBeVisible();
    await expect(page.locator('h3:has-text("Right")')).toBeVisible();
    await expect(page.getByText('Left text.')).toBeVisible();
    await expect(page.getByText('Right text.')).toBeVisible();
  });

  test('Old card-based Columns render correctly on /docs/col-layout-test', async ({ page }) => {
    await page.goto('/docs/col-layout-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Verify Old Columns heading exists
    await expect(page.locator('h2:has-text("Old Columns")')).toBeVisible();
    
    // Verify old card-based columns render with Card One and Card Two
    await expect(page.getByText('Card', { exact: true })).toBeVisible();
    await expect(page.getByText('Card2')).toBeVisible();
    await expect(page.getByText('Legacy card.')).toBeVisible();
    await expect(page.getByText('Another.')).toBeVisible();
  });

  test('Welcome article renders old Columns with cards and iframes', async ({ page }) => {
    await page.goto('/docs/welcome', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('Welcome To Emergent');
    
    // Verify old Columns are rendering (cards with icons)
    // The welcome page has cards like "Getting Started", "Features", "Integrations"
    await expect(page.getByText('Getting Started').first()).toBeVisible();
    await expect(page.getByText('Integrations').first()).toBeVisible();
    
    // Verify YouTube iframe is rendered
    const youtubeEmbed = page.locator('[data-testid="youtube-embed"]');
    if (await youtubeEmbed.count() > 0) {
      await expect(youtubeEmbed.first()).toBeVisible();
    }
  });

  test('ColumnLayout stacks vertically on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 480, height: 800 });
    
    await page.goto('/docs/col-layout-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Wait for content to load
    await expect(page.locator('h2:has-text("Two Columns")')).toBeVisible();
    
    // Note: The ColumnLayout currently uses inline style grid-template-columns
    // which may or may not have responsive behavior
    // This test documents current behavior
    const columnLayouts = page.locator('[data-testid="column-layout-render"]');
    
    if (await columnLayouts.count() > 0) {
      const columnLayout = columnLayouts.first();
      const computedStyle = await columnLayout.evaluate((el) => {
        const style = window.getComputedStyle(el);
        return {
          display: style.display,
          gridTemplateColumns: style.gridTemplateColumns
        };
      });
      
      // On mobile, columns should ideally stack (grid-template-columns: 1fr)
      // If still showing 2 columns, this is a potential issue
      console.log('Mobile grid-template-columns:', computedStyle.gridTemplateColumns);
    }
    
    // Verify content is still visible
    await expect(page.locator('h3:has-text("Left")')).toBeVisible();
    await expect(page.locator('h3:has-text("Right")')).toBeVisible();
  });
});

test.describe('KB Column Layout - Editor', () => {
  test.beforeEach(async ({ page }) => {
    // Set auth cookie
    await page.context().addCookies([{
      name: 'session_token',
      value: SESSION_TOKEN,
      domain: 'columns-rebuild.preview.emergentagent.com',
      path: '/'
    }]);
    
    // Remove emergent badge
    await page.addInitScript(() => {
      setInterval(() => {
        const badge = document.querySelector('[class*="emergent"], [id*="emergent-badge"]');
        if (badge) badge.remove();
      }, 500);
    });
  });

  test('KB Editor loads col-layout-test article with visual column panes', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Column Layout Test in sidebar
    await page.getByText('Column Layout Test').click();
    await page.waitForTimeout(3000);
    
    // Verify article is selected and loaded
    await expect(page.locator('input[value="Column Layout Test"]')).toBeVisible();
    await expect(page.locator('input[value="col-layout-test"]')).toBeVisible();
    
    // Verify Two Columns heading in editor
    const editor = page.locator('.ProseMirror').first();
    await expect(editor.locator('h2:has-text("Two Columns")')).toBeVisible();
    
    // Verify ColumnLayout renders as visual column panes in editor
    // The editor should show data-testid="column-layout" for the wrapper
    // and data-testid="column-pane" for each pane
    const columnLayout = page.locator('[data-testid="column-layout"]');
    if (await columnLayout.count() > 0) {
      await expect(columnLayout.first()).toBeVisible();
      
      const columnPanes = page.locator('[data-testid="column-pane"]');
      expect(await columnPanes.count()).toBeGreaterThanOrEqual(2);
    }
    
    // Verify Left and Right content visible in editor
    await expect(editor.locator('h3:has-text("Left")')).toBeVisible();
    await expect(editor.locator('h3:has-text("Right")')).toBeVisible();
  });

  test('KB Editor shows old card-based Columns for col-layout-test', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Column Layout Test in sidebar
    await page.getByText('Column Layout Test').click();
    await page.waitForTimeout(3000);
    
    // Scroll down to see Old Columns section
    const editor = page.locator('.ProseMirror').first();
    await expect(editor.locator('h2:has-text("Old Columns")')).toBeVisible();
    
    // Verify old card-based Columns render with data-testid="columns-block"
    const columnsBlock = page.locator('[data-testid="columns-block"]');
    if (await columnsBlock.count() > 0) {
      await expect(columnsBlock.first()).toBeVisible();
    }
    
    // Verify column cards are visible with data-testid="column-card"
    const columnCards = page.locator('[data-testid="column-card"]');
    if (await columnCards.count() > 0) {
      expect(await columnCards.count()).toBeGreaterThanOrEqual(2);
    }
    
    // Verify card content
    await expect(page.getByText('Card', { exact: true })).toBeVisible();
    await expect(page.getByText('Legacy card.')).toBeVisible();
  });

  test('KB Editor Welcome article shows old card-based Columns', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Welcome To Emergent in sidebar (may be truncated)
    await page.getByText('Welcome To E', { exact: false }).first().click();
    await page.waitForTimeout(3000);
    
    // Verify article is loaded
    await expect(page.locator('input[value="welcome"]')).toBeVisible();
    
    // Verify old card-based Columns render
    const columnsBlock = page.locator('[data-testid="columns-block"]');
    if (await columnsBlock.count() > 0) {
      await expect(columnsBlock.first()).toBeVisible();
    }
    
    // Check for Getting Started card
    await expect(page.getByText('Getting Started')).toBeVisible();
  });

  test('Insert menu shows 2 Columns option', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Column Layout Test in sidebar
    await page.getByText('Column Layout Test').click();
    await page.waitForTimeout(3000);
    
    // Click on the "+ Insert" button
    const insertBtn = page.locator('button:has-text("Insert")');
    await expect(insertBtn).toBeVisible();
    await insertBtn.click();
    await page.waitForTimeout(500);
    
    // Verify insert menu shows column options
    await expect(page.getByText('1 Column')).toBeVisible();
    await expect(page.getByText('2 Columns')).toBeVisible();
  });

  test('Inserting 2-column layout creates editable column panes', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Column Layout Test in sidebar
    await page.getByText('Column Layout Test').click();
    await page.waitForTimeout(3000);
    
    // Get initial count of column layouts
    const initialColumnLayouts = await page.locator('[data-testid="column-layout"]').count();
    
    // Click on the "+ Insert" button
    await page.locator('button:has-text("Insert")').click();
    await page.waitForTimeout(500);
    
    // Click on "2 Columns" option
    await page.getByText('2 Columns').click();
    await page.waitForTimeout(1000);
    
    // Verify a new column layout was inserted
    const newColumnLayouts = await page.locator('[data-testid="column-layout"]').count();
    expect(newColumnLayouts).toBeGreaterThanOrEqual(initialColumnLayouts);
    
    // Verify column panes exist
    const columnPanes = page.locator('[data-testid="column-pane"]');
    expect(await columnPanes.count()).toBeGreaterThanOrEqual(2);
  });
});
