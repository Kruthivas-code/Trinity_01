/**
 * KB Editor Redesign E2E Tests
 * Tests for the redesigned /dashboard/kb-editor page
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'https://repo-builder-71.preview.emergentagent.com';
const SESSION_TOKEN = 'test_kb_editor_session_2026';

async function authenticateKBEditor(page: Page) {
  await page.context().addCookies([{
    name: 'session_token',
    value: SESSION_TOKEN,
    domain: 'trinity-docs-v2.preview.emergentagent.com',
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'None'
  }]);
}

test.describe('KB Editor Page Load', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
  });

  test('KB Editor page loads with main components', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    
    // Wait for page to load
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('editor-header')).toBeVisible();
    await expect(page.getByTestId('editor-sidebar')).toBeVisible();
  });

  test('First article is auto-selected on load', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    
    // Wait for page and editor area
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    // The URL should be redirected to include a slug (first article)
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
    
    // Editor main area should have content
    await expect(page.getByTestId('editor-main-area')).toBeVisible();
    
    // Title input should have a value (first article loaded)
    const titleInput = page.getByTestId('editor-title-input');
    await expect(titleInput).toBeVisible();
    const titleValue = await titleInput.inputValue();
    expect(titleValue.length).toBeGreaterThan(0);
  });
});

test.describe('Document Section', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
  });

  test('Document section shows Title field (required)', async ({ page }) => {
    const titleInput = page.getByTestId('editor-title-input');
    await expect(titleInput).toBeVisible();
    
    // Should have required indicator nearby
    const documentSection = page.getByTestId('document-section');
    await expect(documentSection.locator('text=Title')).toBeVisible();
    await expect(documentSection.locator('text=*').first()).toBeVisible();
  });

  test('Document section shows Description field', async ({ page }) => {
    const descInput = page.getByTestId('editor-description-input');
    await expect(descInput).toBeVisible();
    await expect(descInput).toHaveAttribute('placeholder', /description/i);
  });

  test('Document section shows Slug field (required)', async ({ page }) => {
    const slugInput = page.getByTestId('editor-slug-input');
    await expect(slugInput).toBeVisible();
    
    const documentSection = page.getByTestId('document-section');
    await expect(documentSection.locator('text=Slug')).toBeVisible();
  });

  test('Slug field shows URL preview', async ({ page }) => {
    // Load an existing article that has a slug
    const slugInput = page.getByTestId('editor-slug-input');
    await expect(slugInput).toBeVisible();
    
    const slugValue = await slugInput.inputValue();
    if (slugValue) {
      const slugPreview = page.getByTestId('slug-preview');
      await expect(slugPreview).toBeVisible();
      await expect(slugPreview).toContainText('/docs/');
      await expect(slugPreview).toContainText(slugValue);
    }
  });

  test('Category dropdown is present and functional', async ({ page }) => {
    const categorySelect = page.getByTestId('editor-category-select');
    await expect(categorySelect).toBeVisible();
    
    // Click to open
    await categorySelect.click();
    
    // Should have options
    const options = categorySelect.locator('option');
    const optionCount = await options.count();
    expect(optionCount).toBeGreaterThan(0);
  });

  test('Subcategory dropdown appears when category selected', async ({ page }) => {
    const categorySelect = page.getByTestId('editor-category-select');
    await expect(categorySelect).toBeVisible();
    
    // Check if there's already a category selected
    const currentCategory = await categorySelect.inputValue();
    if (currentCategory) {
      // Subcategory should be visible
      const subcategorySelect = page.getByTestId('editor-subcategory-select');
      await expect(subcategorySelect).toBeVisible();
    }
  });
});

test.describe('Draft/Publish Toggle', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
  });

  test('Draft section with publish toggle is visible', async ({ page }) => {
    const draftSection = page.getByTestId('draft-section');
    await expect(draftSection).toBeVisible();
    
    const publishToggle = page.getByTestId('publish-toggle');
    await expect(publishToggle).toBeVisible();
    await expect(publishToggle).toHaveAttribute('role', 'switch');
  });

  test('Publish toggle can be clicked', async ({ page }) => {
    const publishToggle = page.getByTestId('publish-toggle');
    await expect(publishToggle).toBeVisible();
    
    // Get initial state
    const initialState = await publishToggle.getAttribute('aria-checked');
    
    // Click toggle
    await publishToggle.click();
    
    // State should change
    const newState = await publishToggle.getAttribute('aria-checked');
    expect(newState).not.toBe(initialState);
  });
});

test.describe('Save Button Validation', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
  });

  test('Save button disabled when Title is empty', async ({ page }) => {
    // Navigate to new article
    await page.goto('/dashboard/kb-editor/new', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    const saveBtn = page.getByTestId('save-btn');
    const titleInput = page.getByTestId('editor-title-input');
    
    // Clear title
    await titleInput.fill('');
    
    // Save should be disabled
    await expect(saveBtn).toBeDisabled();
  });

  test('Save button disabled when Slug is empty', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/new', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    const saveBtn = page.getByTestId('save-btn');
    const titleInput = page.getByTestId('editor-title-input');
    const slugInput = page.getByTestId('editor-slug-input');
    
    // Fill title but clear slug
    await titleInput.fill('Test Article');
    await slugInput.fill('');
    
    // Save should be disabled
    await expect(saveBtn).toBeDisabled();
  });

  test('Save button enabled when Title and Slug have values', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/new', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    const saveBtn = page.getByTestId('save-btn');
    const titleInput = page.getByTestId('editor-title-input');
    const slugInput = page.getByTestId('editor-slug-input');
    
    // Fill title first - this auto-fills slug
    await titleInput.fill('Test Article Title');
    // Wait for auto-slug to be generated
    await expect(slugInput).toHaveValue(/test-article-title/i);
    
    // Optionally override slug
    await slugInput.fill('test-article-slug');
    await expect(slugInput).toHaveValue('test-article-slug');
    
    // Both fields should have values now
    await expect(titleInput).toHaveValue('Test Article Title');
    
    // Save should be enabled
    await expect(saveBtn).toBeEnabled();
  });
});

test.describe('Rich Text Editor', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
  });

  test('WYSIWYG editor is visible', async ({ page }) => {
    const richTextEditor = page.getByTestId('rich-text-editor');
    await expect(richTextEditor).toBeVisible();
    
    const toolbar = page.getByTestId('editor-toolbar');
    await expect(toolbar).toBeVisible();
  });

  test('Insert menu dropdown shows options', async ({ page }) => {
    const insertBtn = page.getByTestId('insert-btn');
    await expect(insertBtn).toBeVisible();
    
    // Click to open menu
    await insertBtn.click();
    
    // Insert menu should appear
    const insertMenu = page.getByTestId('insert-menu');
    await expect(insertMenu).toBeVisible();
    
    // Check for some expected options
    await expect(page.getByTestId('insert-callout_note')).toBeVisible();
    await expect(page.getByTestId('insert-callout_tip')).toBeVisible();
    await expect(page.getByTestId('insert-steps')).toBeVisible();
    await expect(page.getByTestId('insert-tabs')).toBeVisible();
    await expect(page.getByTestId('insert-accordion')).toBeVisible();
    await expect(page.getByTestId('insert-code_block')).toBeVisible();
  });

  test('Heading dropdown shows H1-H6 options', async ({ page }) => {
    const headingDropdown = page.getByTestId('heading-dropdown');
    await expect(headingDropdown).toBeVisible();
    
    // Click to open
    await headingDropdown.click();
    
    // Heading menu should appear
    const headingMenu = page.getByTestId('heading-menu');
    await expect(headingMenu).toBeVisible();
    
    // Check for heading options (level 0 = Paragraph, 1-6 = H1-H6)
    await expect(page.getByTestId('heading-0')).toBeVisible(); // Paragraph
    await expect(page.getByTestId('heading-1')).toBeVisible(); // H1
    await expect(page.getByTestId('heading-2')).toBeVisible(); // H2
    await expect(page.getByTestId('heading-3')).toBeVisible(); // H3
    await expect(page.getByTestId('heading-6')).toBeVisible(); // H6
  });

  test('Toolbar has formatting buttons', async ({ page }) => {
    // Check for various toolbar buttons
    await expect(page.getByTestId('toolbar-bold')).toBeVisible();
    await expect(page.getByTestId('toolbar-italic')).toBeVisible();
    await expect(page.getByTestId('toolbar-link')).toBeVisible();
    await expect(page.getByTestId('toolbar-blockquote')).toBeVisible();
    await expect(page.getByTestId('toolbar-bullet-list')).toBeVisible();
    await expect(page.getByTestId('toolbar-ordered-list')).toBeVisible();
  });
});

test.describe('Global Docs Settings Modal', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
  });

  test('Global settings button opens modal', async ({ page }) => {
    const settingsToggle = page.getByTestId('global-settings-toggle');
    await expect(settingsToggle).toBeVisible();
    
    // Click to open modal
    await settingsToggle.click();
    
    // Modal should appear
    const modal = page.getByTestId('global-settings-modal');
    await expect(modal).toBeVisible();
  });

  test('Global settings modal has all fields', async ({ page }) => {
    // Open modal
    await page.getByTestId('global-settings-toggle').click();
    await expect(page.getByTestId('global-settings-modal')).toBeVisible();
    
    // Wait for loading to complete
    await expect(page.getByTestId('settings-meta_title')).toBeVisible({ timeout: 5000 });
    
    // Check for all 7 fields
    await expect(page.getByTestId('settings-meta_title')).toBeVisible();
    await expect(page.getByTestId('settings-meta_description')).toBeVisible();
    await expect(page.getByTestId('settings-favicon_url')).toBeVisible();
    await expect(page.getByTestId('settings-og_image_url')).toBeVisible();
    await expect(page.getByTestId('settings-logo_url')).toBeVisible();
    await expect(page.getByTestId('settings-footer_text')).toBeVisible();
    await expect(page.getByTestId('settings-custom_domain')).toBeVisible();
  });

  test('Global settings modal has Save and Cancel buttons', async ({ page }) => {
    await page.getByTestId('global-settings-toggle').click();
    await expect(page.getByTestId('global-settings-modal')).toBeVisible();
    
    await expect(page.getByTestId('global-settings-save')).toBeVisible();
    await expect(page.getByTestId('global-settings-cancel')).toBeVisible();
  });

  test('Global settings modal closes via X button', async ({ page }) => {
    await page.getByTestId('global-settings-toggle').click();
    await expect(page.getByTestId('global-settings-modal')).toBeVisible();
    
    // Close via X
    await page.getByTestId('global-settings-close').click();
    
    await expect(page.getByTestId('global-settings-modal')).not.toBeVisible();
  });

  test('Global settings modal closes via Cancel button', async ({ page }) => {
    await page.getByTestId('global-settings-toggle').click();
    await expect(page.getByTestId('global-settings-modal')).toBeVisible();
    
    // Close via Cancel
    await page.getByTestId('global-settings-cancel').click();
    
    await expect(page.getByTestId('global-settings-modal')).not.toBeVisible();
  });
});

test.describe('New Article Creation', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
  });

  test('New article button navigates to new article form', async ({ page }) => {
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
    
    // Click new article button
    await page.getByTestId('new-article-btn').click();
    
    // Should navigate to /new
    await expect(page).toHaveURL(/\/dashboard\/kb-editor\/new/);
    
    // Form should be empty
    const titleInput = page.getByTestId('editor-title-input');
    await expect(titleInput).toHaveValue('');
  });

  test('New article defaults to draft (unpublished)', async ({ page }) => {
    await page.goto('/dashboard/kb-editor/new', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    // Check publish toggle is off (draft)
    const publishToggle = page.getByTestId('publish-toggle');
    await expect(publishToggle).toHaveAttribute('aria-checked', 'false');
    
    // Should show "Draft" text (using exact match for p tag with text Draft)
    const draftSection = page.getByTestId('draft-section');
    await expect(draftSection.getByText('Draft', { exact: true })).toBeVisible();
  });
});

test.describe('Header Actions', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
    await page.goto('/dashboard/kb-editor', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    await page.waitForURL(/\/dashboard\/kb-editor\/[\w-]+/, { timeout: 10000 });
  });

  test('Theme toggle button works', async ({ page }) => {
    const themeToggle = page.getByTestId('kb-editor-theme-toggle');
    await expect(themeToggle).toBeVisible();
    
    // Click should toggle theme
    await themeToggle.click();
    
    // Should still be functional after toggle
    await expect(page.getByTestId('kb-editor-page')).toBeVisible();
  });

  test('Social links toggle opens panel', async ({ page }) => {
    const socialLinksToggle = page.getByTestId('social-links-toggle');
    await expect(socialLinksToggle).toBeVisible();
    
    await socialLinksToggle.click();
    
    // Panel should appear (specific testid for the panel)
    await expect(page.getByTestId('social-links-panel')).toBeVisible();
  });

  test('Back to dashboard link is present', async ({ page }) => {
    const backLink = page.getByTestId('back-to-dashboard');
    await expect(backLink).toBeVisible();
  });

  test('Live preview link present for existing articles', async ({ page }) => {
    const livePreviewLink = page.getByTestId('live-preview-link');
    await expect(livePreviewLink).toBeVisible();
    await expect(livePreviewLink).toHaveAttribute('target', '_blank');
  });
});


test.describe('TOC (On This Page) Section', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateKBEditor(page);
  });

  test('TOC section shows H2/H3 headings from article content', async ({ page }) => {
    // Navigate to an article with headings in content
    await page.goto('/dashboard/kb-editor/welcome', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    // The TOC section should be visible if article has H2/H3 headings
    const tocSection = page.getByTestId('toc-section');
    
    // If TOC section is visible, check that it has heading items
    const tocVisible = await tocSection.isVisible().catch(() => false);
    if (tocVisible) {
      // Should have "On This Page" header
      await expect(tocSection.locator('text=On This Page')).toBeVisible();
      
      // Should have at least one TOC item
      const firstTocItem = page.getByTestId('toc-item-0');
      await expect(firstTocItem).toBeVisible();
    }
  });

  test('TOC section not shown when article has no H2/H3 headings', async ({ page }) => {
    // Navigate to new article (no content yet)
    await page.goto('/dashboard/kb-editor/new', { waitUntil: 'domcontentloaded' });
    await expect(page.getByTestId('kb-editor-page')).toBeVisible({ timeout: 15000 });
    
    // TOC section should not be visible for empty content
    const tocSection = page.getByTestId('toc-section');
    await expect(tocSection).not.toBeVisible();
  });
});
