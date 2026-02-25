import { test, expect } from '@playwright/test';
import { authenticateAndNavigate } from '../fixtures/helpers';

test.describe('Sidebar Navigation - Density Fix', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
  });

  test('Nav items have h-7 height for denser layout', async ({ page }) => {
    // Get the desktop sidebar dashboard nav item (first one)
    const dashboardNav = page.locator('[data-testid="nav-dashboard"]').first();
    await expect(dashboardNav).toBeVisible();
    
    // Check that it has the h-7 class (28px height)
    const hasH7Class = await dashboardNav.evaluate(el => el.classList.contains('h-7'));
    expect(hasH7Class).toBe(true);
    
    // Verify actual height is around 28px (h-7 = 1.75rem = 28px at 16px base)
    const boundingBox = await dashboardNav.boundingBox();
    expect(boundingBox).not.toBeNull();
    if (boundingBox) {
      // Allow some tolerance for padding/borders
      expect(boundingBox.height).toBeGreaterThanOrEqual(24);
      expect(boundingBox.height).toBeLessThanOrEqual(32);
    }
  });

  test('Tickets section nav items are visible and dense', async ({ page }) => {
    // Verify key nav items exist (use .first() to get desktop sidebar)
    const allTicketsNav = page.locator('[data-testid="nav-all-tickets"]').first();
    await expect(allTicketsNav).toBeVisible();
    
    // Verify h-7 class for dense layout
    const hasH7Class = await allTicketsNav.evaluate(el => el.classList.contains('h-7'));
    expect(hasH7Class).toBe(true);
    
    // Also check starred and open
    await expect(page.locator('[data-testid="nav-starred-tickets"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="nav-open-tickets"]').first()).toBeVisible();
  });

  test('Escalation folders with L1 L2 L3 are visible', async ({ page }) => {
    // Use role-based locators for more stability
    const l1 = page.getByRole('button', { name: /L1/i }).first();
    const l2 = page.getByRole('button', { name: /L2/i }).first();
    const l3 = page.getByRole('button', { name: /L3/i }).first();
    
    // At least L1 should be visible (may need to expand escalation)
    await expect(l1).toBeVisible({ timeout: 10000 });
    await expect(l2).toBeVisible();
    await expect(l3).toBeVisible();
  });

});

test.describe('Custom Inbox Features', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
    // Wait for full page load including inboxes
    await page.waitForLoadState('networkidle');
  });

  test('Custom inboxes are shown in sidebar', async ({ page }) => {
    // Wait for sidebar to stabilize
    await page.waitForSelector('[data-testid="nav-all-tickets"]', { timeout: 10000 });
    
    // Scroll sidebar to reveal custom inboxes if needed
    const sidebar = page.locator('[data-testid="sidebar"]').first();
    if (await sidebar.isVisible()) {
      await sidebar.evaluate(el => {
        const scrollableArea = el.querySelector('.overflow-y-auto');
        if (scrollableArea) scrollableArea.scrollTop = 500;
      });
    }
    
    // Wait a bit for scroll to settle
    await page.waitForTimeout(500);
    
    // Look for custom inbox items
    const customInboxes = page.locator('[data-testid^="sidebar-inbox-"]');
    const inboxCount = await customInboxes.count();
    
    // Should have at least one custom inbox
    expect(inboxCount).toBeGreaterThan(0);
  });

  test('Custom inbox menu shows correct options', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForLoadState('networkidle');
    
    // Scroll to reveal custom inboxes
    const sidebar = page.locator('[data-testid="sidebar"]').first();
    if (await sidebar.isVisible()) {
      await sidebar.evaluate(el => {
        const scrollableArea = el.querySelector('.overflow-y-auto');
        if (scrollableArea) scrollableArea.scrollTop = 300;
      });
    }
    
    await page.waitForTimeout(500);
    
    // Find a custom inbox
    const customInboxes = page.locator('[data-testid^="sidebar-inbox-"]');
    const firstInbox = customInboxes.first();
    
    if (await firstInbox.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Hover to show menu trigger
      await firstInbox.hover();
      await page.waitForTimeout(300);
      
      // Click menu trigger
      const menuTrigger = firstInbox.locator('[data-testid^="inbox-menu-trigger-"]');
      if (await menuTrigger.isVisible({ timeout: 2000 }).catch(() => false)) {
        await menuTrigger.click();
        
        // Verify menu appears with correct options
        await expect(page.locator('text=Rename').first()).toBeVisible({ timeout: 5000 });
        await expect(page.locator('text=Edit filters').first()).toBeVisible();
        await expect(page.locator('text=Share').first()).toBeVisible();
        await expect(page.locator('text=Delete').first()).toBeVisible();
        
        // Close menu
        await page.keyboard.press('Escape');
      }
    }
  });

  test('Navigation from sidebar works correctly', async ({ page }) => {
    // Click Dashboard (use .first())
    const dashboardNav = page.locator('[data-testid="nav-dashboard"]').first();
    await dashboardNav.click();
    
    // Verify navigation to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Navigate back to all-tickets
    const allTicketsNav = page.locator('[data-testid="nav-all-tickets"]').first();
    await allTicketsNav.click();
    
    // Verify URL
    await expect(page).toHaveURL(/\/all-tickets/);
    
    // Verify page title in header
    await expect(page.getByRole('heading', { name: 'All Tickets' })).toBeVisible();
  });

});
