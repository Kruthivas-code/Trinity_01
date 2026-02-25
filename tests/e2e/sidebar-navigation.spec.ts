import { test, expect } from '@playwright/test';
import { authenticateAndNavigate } from '../fixtures/helpers';

test.describe('Sidebar Navigation - Density Fix', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
  });

  test('Nav items have h-7 height for denser layout', async ({ page }) => {
    // Wait for sidebar
    await page.waitForSelector('[data-testid="nav-dashboard"]', { timeout: 10000 });
    
    // Get the dashboard nav item
    const dashboardNav = page.locator('[data-testid="nav-dashboard"]');
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

  test('Tickets section nav items are visible', async ({ page }) => {
    // Verify key nav items exist
    await expect(page.locator('[data-testid="nav-all-tickets"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-starred-tickets"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-open-tickets"]')).toBeVisible();
  });

  test('Escalation folders are visible', async ({ page }) => {
    // Wait for sidebar to load
    await page.waitForSelector('text=Escalation', { timeout: 10000 });
    
    // L1, L2, L3 should be visible
    const l1 = page.locator('text=L1').first();
    const l2 = page.locator('text=L2').first();
    const l3 = page.locator('text=L3').first();
    
    await expect(l1).toBeVisible();
    await expect(l2).toBeVisible();
    await expect(l3).toBeVisible();
  });

});

test.describe('Custom Inbox Deletion Navigation', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
  });

  test('Custom inboxes are shown in sidebar', async ({ page }) => {
    // Wait for sidebar
    await page.waitForSelector('[data-testid="nav-all-tickets"]', { timeout: 10000 });
    
    // Expand tickets section if needed
    const ticketsToggle = page.locator('[data-testid="nav-tickets-toggle"]');
    await ticketsToggle.click();
    
    // Look for custom inbox items (they have sidebar-inbox- prefix in testid)
    const customInboxes = page.locator('[data-testid^="sidebar-inbox-"]');
    const inboxCount = await customInboxes.count();
    
    // Should have at least one custom inbox (based on screenshot showing TEST_ inboxes)
    expect(inboxCount).toBeGreaterThan(0);
  });

  test('Custom inbox menu has delete option', async ({ page }) => {
    // Wait for sidebar
    await page.waitForSelector('[data-testid="nav-all-tickets"]', { timeout: 10000 });
    
    // Expand tickets section
    const ticketsToggle = page.locator('[data-testid="nav-tickets-toggle"]');
    await ticketsToggle.click();
    
    // Find a custom inbox
    const customInboxes = page.locator('[data-testid^="sidebar-inbox-"]');
    const firstInbox = customInboxes.first();
    
    if (await firstInbox.isVisible()) {
      // Hover to show menu trigger
      await firstInbox.hover();
      
      // Look for the menu trigger (3-dot button)
      const menuTrigger = firstInbox.locator('[data-testid^="inbox-menu-trigger-"]');
      
      if (await menuTrigger.isVisible()) {
        await menuTrigger.click();
        
        // Menu should appear with delete option
        // Note: We won't actually delete to avoid breaking other tests
        const menu = page.locator('[data-testid^="inbox-menu-"]').first();
        await expect(menu).toBeVisible({ timeout: 5000 });
        
        // Should have Rename, Edit filters, Share, and Delete options
        await expect(menu.locator('text=Rename')).toBeVisible();
        await expect(menu.locator('text=Delete')).toBeVisible();
        
        // Close menu by clicking elsewhere
        await page.keyboard.press('Escape');
      }
    }
  });

  test('Navigation to /all-tickets works from sidebar', async ({ page }) => {
    // Click All Tickets
    const allTicketsNav = page.locator('[data-testid="nav-all-tickets"]');
    await allTicketsNav.click();
    
    // Verify URL
    await expect(page).toHaveURL(/\/all-tickets/);
    
    // Verify tickets list is visible
    await expect(page.locator('text=All Tickets')).toBeVisible();
  });

});
