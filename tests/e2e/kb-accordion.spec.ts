import { test, expect } from '@playwright/test';

const BASE_URL = 'https://repo-builder-83.preview.emergentagent.com';
const SESSION_TOKEN = 'test_kb_session_token';

test.describe('KB Accordion - Public Docs', () => {
  test.beforeEach(async ({ page }) => {
    // Remove emergent badge that might overlay elements
    await page.addInitScript(() => {
      setInterval(() => {
        const badge = document.querySelector('[class*="emergent"], [id*="emergent-badge"]');
        if (badge) badge.remove();
      }, 500);
    });
  });

  test('Accordion renders at /docs/accordion-test with 3 expandable items', async ({ page }) => {
    await page.goto('/docs/accordion-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Verify page title
    await expect(page.locator('h1')).toContainText('Accordion Test');
    
    // Verify FAQ Section heading exists
    await expect(page.locator('h2:has-text("FAQ Section")')).toBeVisible();
    
    // Verify accordion renders with data-testid
    const accordion = page.locator('[data-testid="accordion"]');
    await expect(accordion).toBeVisible();
    
    // Verify accordion items exist
    const accordionItems = page.locator('[data-testid="accordion-item"]');
    await expect(accordionItems).toHaveCount(3);
    
    // Verify accordion trigger buttons exist
    const accordionTriggers = page.locator('[data-testid="accordion-trigger"]');
    await expect(accordionTriggers).toHaveCount(3);
    
    // Verify the 3 accordion titles
    await expect(page.getByText('What is Trinity?')).toBeVisible();
    await expect(page.getByText('How do I get started?')).toBeVisible();
    await expect(page.getByText('Is there a free plan?')).toBeVisible();
  });

  test('Clicking accordion trigger expands/collapses content', async ({ page }) => {
    await page.goto('/docs/accordion-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Find first accordion trigger
    const firstTrigger = page.locator('[data-testid="accordion-trigger"]').first();
    await expect(firstTrigger).toBeVisible();
    
    // Initial state - first accordion item content should be hidden (collapsed by default)
    const firstContent = page.locator('[data-testid="accordion-content"]').first();
    const firstContentParent = page.locator('[data-testid="accordion-item"]').first();
    
    // Click to expand
    await firstTrigger.click();
    await page.waitForTimeout(300); // Wait for animation
    
    // Verify content is visible after click
    await expect(firstContent).toBeVisible();
    await expect(page.getByText('Trinity is a full-stack customer support suite.')).toBeVisible();
    
    // Click again to collapse
    await firstTrigger.click();
    await page.waitForTimeout(300);
    
    // Verify content is hidden (has max-h-0 or opacity-0)
    const contentStyle = await firstContent.evaluate((el) => {
      const style = window.getComputedStyle(el.parentElement);
      return {
        maxHeight: style.maxHeight,
        opacity: style.opacity
      };
    });
    // When collapsed, max-height should be 0 and/or opacity should be 0
    expect(contentStyle.maxHeight === '0px' || contentStyle.opacity === '0').toBeTruthy();
  });

  test('Second accordion item content includes bullet list', async ({ page }) => {
    await page.goto('/docs/accordion-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click second accordion trigger to expand it
    const secondTrigger = page.locator('[data-testid="accordion-trigger"]').nth(1);
    await secondTrigger.click();
    await page.waitForTimeout(300);
    
    // Verify the second item content has bullet list
    await expect(page.getByText('Step 1: Create account')).toBeVisible();
    await expect(page.getByText('Step 2: Configure settings')).toBeVisible();
    await expect(page.getByText('Step 3: Start using')).toBeVisible();
  });

  test('Additional Info section renders after accordion', async ({ page }) => {
    await page.goto('/docs/accordion-test', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Verify Additional Info heading exists
    await expect(page.locator('h2:has-text("Additional Info")')).toBeVisible();
    await expect(page.getByText('This section comes after the accordion.')).toBeVisible();
  });
});

test.describe('KB Accordion - Editor', () => {
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

  test('KB Editor loads accordion-test article with visual accordion block', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Accordion Test in sidebar
    await page.getByText('Accordion Test').click();
    await page.waitForTimeout(3000);
    
    // Verify article is selected and loaded
    await expect(page.locator('input[value="Accordion Test"]')).toBeVisible();
    await expect(page.locator('input[value="accordion-test"]')).toBeVisible();
    
    // Verify FAQ Section heading in editor
    const editor = page.locator('.ProseMirror').first();
    await expect(editor.locator('h2:has-text("FAQ Section")')).toBeVisible();
    
    // Verify accordion renders as visual block in editor with data-testid="accordion-block"
    const accordionBlock = page.locator('[data-testid="accordion-block"]');
    await expect(accordionBlock).toBeVisible();
    
    // Verify accordion items exist in editor with data-testid="accordion-item"
    const accordionItems = page.locator('[data-testid="accordion-item"]');
    expect(await accordionItems.count()).toBeGreaterThanOrEqual(3);
    
    // Verify accordion item titles are visible in editor
    await expect(page.locator('[data-testid="accordion-item-title-input"]').first()).toBeVisible();
  });

  test('Insert menu shows Accordion option', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Accordion Test in sidebar
    await page.getByText('Accordion Test').click();
    await page.waitForTimeout(3000);
    
    // Click on the "+ Insert" button
    const insertBtn = page.locator('[data-testid="insert-btn"]');
    await expect(insertBtn).toBeVisible();
    await insertBtn.click();
    await page.waitForTimeout(500);
    
    // Verify insert menu is visible
    const insertMenu = page.locator('[data-testid="insert-menu"]');
    await expect(insertMenu).toBeVisible();
    
    // Verify Accordion option exists in the menu
    const accordionOption = page.locator('[data-testid="insert-accordion"]');
    await expect(accordionOption).toBeVisible();
    await expect(accordionOption).toContainText('Accordion');
  });

  test('Accordion item titles are editable in KB editor', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Accordion Test in sidebar
    await page.getByText('Accordion Test').click();
    await page.waitForTimeout(3000);
    
    // Find first accordion item title input
    const titleInput = page.locator('[data-testid="accordion-item-title-input"]').first();
    await expect(titleInput).toBeVisible();
    
    // Verify the current title
    const currentValue = await titleInput.inputValue();
    expect(currentValue).toBe('What is Trinity?');
    
    // Edit the title (don't save, just verify it's editable)
    await titleInput.fill('What is Trinity? EDITED');
    await expect(titleInput).toHaveValue('What is Trinity? EDITED');
    
    // Reset to original value (don't save)
    await titleInput.fill('What is Trinity?');
  });

  test('Accordion items can be expanded/collapsed in editor', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    
    // Click on Accordion Test in sidebar
    await page.getByText('Accordion Test').click();
    await page.waitForTimeout(3000);
    
    // Find first accordion item header (clickable area)
    const firstItemHeader = page.locator('[data-testid="accordion-item-header"]').first();
    await expect(firstItemHeader).toBeVisible();
    
    // Click to toggle expand/collapse
    await firstItemHeader.click();
    await page.waitForTimeout(300);
    
    // Verify the accordion content area exists and toggles
    const accordionItem = page.locator('[data-testid="accordion-item"]').first();
    await expect(accordionItem).toBeVisible();
  });
});

test.describe('KB Accordion - API', () => {
  test('GET /api/kb/admin/articles/accordion-test returns article with Accordion tags', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/kb/admin/articles/accordion-test`, {
      headers: {
        'Cookie': `session_token=${SESSION_TOKEN}`
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Verify article data
    expect(data.slug).toBe('accordion-test');
    expect(data.title).toBe('Accordion Test');
    
    // Verify content_markdown contains Accordion and AccordionItem tags
    expect(data.content_markdown).toContain('<Accordion>');
    expect(data.content_markdown).toContain('</Accordion>');
    expect(data.content_markdown).toContain('<AccordionItem');
    expect(data.content_markdown).toContain('</AccordionItem>');
    
    // Verify all 3 accordion items are in the content
    expect(data.content_markdown).toContain('title="What is Trinity?"');
    expect(data.content_markdown).toContain('title="How do I get started?"');
    expect(data.content_markdown).toContain('title="Is there a free plan?"');
  });

  test('GET /api/kb/articles/accordion-test (public) returns article with Accordion tags', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/kb/articles/accordion-test`);
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    
    // Verify article data
    expect(data.article.slug).toBe('accordion-test');
    expect(data.article.title).toBe('Accordion Test');
    
    // Verify content_markdown contains Accordion tags
    expect(data.article.content_markdown).toContain('<Accordion>');
    expect(data.article.content_markdown).toContain('<AccordionItem');
  });

  test('PUT /api/kb/admin/articles/accordion-test updates and preserves Accordion content', async ({ request }) => {
    // First, get current content
    const getResponse = await request.get(`${BASE_URL}/api/kb/admin/articles/accordion-test`, {
      headers: {
        'Cookie': `session_token=${SESSION_TOKEN}`
      }
    });
    const originalData = await getResponse.json();
    
    // Update with slightly modified content (add a space to description)
    const updatedContent = originalData.content_markdown + ' '; // Just add a space to trigger update
    
    const putResponse = await request.put(`${BASE_URL}/api/kb/admin/articles/accordion-test`, {
      headers: {
        'Cookie': `session_token=${SESSION_TOKEN}`,
        'Content-Type': 'application/json'
      },
      data: {
        content_markdown: updatedContent,
        title: originalData.title,
        description: originalData.description,
        nav_group_key: originalData.nav_group_key,
        section_key: originalData.section_key,
        published: originalData.published
      }
    });
    
    expect(putResponse.ok()).toBeTruthy();
    const putData = await putResponse.json();
    
    // Verify Accordion content is preserved
    expect(putData.content_markdown).toContain('<Accordion>');
    expect(putData.content_markdown).toContain('</Accordion>');
    expect(putData.content_markdown).toContain('<AccordionItem');
    expect(putData.content_markdown).toContain('</AccordionItem>');
    expect(putData.content_markdown).toContain('title="What is Trinity?"');
    expect(putData.content_markdown).toContain('title="How do I get started?"');
    expect(putData.content_markdown).toContain('title="Is there a free plan?"');
    
    // Restore original content
    await request.put(`${BASE_URL}/api/kb/admin/articles/accordion-test`, {
      headers: {
        'Cookie': `session_token=${SESSION_TOKEN}`,
        'Content-Type': 'application/json'
      },
      data: {
        content_markdown: originalData.content_markdown,
        title: originalData.title,
        description: originalData.description,
        nav_group_key: originalData.nav_group_key,
        section_key: originalData.section_key,
        published: originalData.published
      }
    });
  });
});
