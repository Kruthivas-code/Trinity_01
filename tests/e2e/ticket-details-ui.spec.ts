import { test, expect } from '@playwright/test';
import { authenticateAndNavigate, openTicketDrawer } from '../fixtures/helpers';

const TEST_TICKET_1 = 'TKT-024453'; // Has 'email' tag

test.describe('Ticket Details Panel - UI Fixes', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
  });

  test('Tags display without # prefix', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_1);
    
    // Wait for details panel to load
    await page.waitForSelector('[data-testid="tag-input"]', { timeout: 10000 });
    
    // Find the tags section - the "email" tag should be displayed
    const tagsSection = page.locator('text=TAGS').locator('..').locator('..');
    await expect(tagsSection).toBeVisible();
    
    // Look for the email tag without # prefix
    const emailTag = page.locator('.rounded-full').filter({ hasText: 'email' }).first();
    await expect(emailTag).toBeVisible();
    
    // Get the tag text and verify no # prefix
    const tagText = await emailTag.textContent();
    expect(tagText).not.toMatch(/^#/);
    expect(tagText).toContain('email');
  });

  test('Source field shows correctly without Channel field', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_1);
    
    // Wait for attributes section
    await page.waitForSelector('text=ATTRIBUTES', { timeout: 10000 });
    
    // Expand attributes if collapsed
    const attributesToggle = page.locator('text=ATTRIBUTES').locator('..');
    await attributesToggle.click();
    
    // Wait for attributes content
    await page.waitForSelector('text=Source');
    
    // Verify Source field exists
    const sourceLabel = page.locator('text=Source');
    await expect(sourceLabel.first()).toBeVisible();
    
    // Verify "Email" is shown as the source value
    const sourceValue = page.locator('text=Email').first();
    await expect(sourceValue).toBeVisible();
    
    // Verify no "Channel" field exists
    const channelField = page.locator('text=Channel');
    await expect(channelField).toHaveCount(0);
  });

  test('No stray brackets or broken rendering', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_1);
    
    // Wait for drawer to fully render
    await page.waitForSelector('[data-testid="ticket-drawer"]', { timeout: 10000 });
    
    // Get all text content from the details panel
    const detailsPanel = page.locator('[data-testid="ticket-drawer"]');
    const allText = await detailsPanel.textContent();
    
    // Check for stray brackets patterns
    expect(allText).not.toMatch(/\[\s*\]/); // Empty brackets
    expect(allText).not.toMatch(/\[object\s+Object\]/); // JS object string
    expect(allText).not.toMatch(/undefined/i); // Undefined values
    expect(allText).not.toMatch(/NaN/); // NaN values
  });

});

test.describe('Customer History Panel - Stable Order', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
  });

  test('Customer history panel shows related tickets', async ({ page }) => {
    // TKT-023869 has 21 related tickets
    await openTicketDrawer(page, 'TKT-023869');
    
    // Wait for customer history panel
    await page.waitForSelector('[data-testid="customer-history-panel"]', { timeout: 10000 });
    
    const panel = page.locator('[data-testid="customer-history-panel"]');
    await expect(panel).toBeVisible();
    
    // Should show customer name
    await expect(panel.locator('text=Iain Munro')).toBeVisible();
    
    // Should show ticket count badge (21)
    await expect(panel.locator('text=21')).toBeVisible();
  });

  test('Current ticket is highlighted in history panel', async ({ page }) => {
    await openTicketDrawer(page, 'TKT-023869');
    
    // Wait for customer history panel
    await page.waitForSelector('[data-testid="customer-history-panel"]', { timeout: 10000 });
    
    // Current ticket should be highlighted
    const currentTicket = page.locator('[data-testid="current-ticket-item"]');
    await expect(currentTicket).toBeVisible();
    
    // Should contain the ticket ID
    await expect(currentTicket).toContainText('TKT-023869');
  });

  test('Clicking related ticket maintains list order', async ({ page }) => {
    await openTicketDrawer(page, 'TKT-023869');
    
    // Wait for customer history panel
    await page.waitForSelector('[data-testid="customer-history-panel"]', { timeout: 10000 });
    
    // Get all ticket IDs in order before click
    const ticketIds = page.locator('[data-testid="customer-history-panel"]').locator('[class*="font-mono"]');
    const initialOrder = await ticketIds.allTextContents();
    
    // Click on a different related ticket
    const relatedTickets = page.locator('[data-testid^="related-ticket-"]');
    const firstRelated = relatedTickets.first();
    
    if (await firstRelated.isVisible()) {
      await firstRelated.click();
      
      // Wait for page to update
      await page.waitForSelector('[data-testid="ticket-drawer"]', { timeout: 10000 });
      
      // Get order after click
      const afterClickOrder = await ticketIds.allTextContents();
      
      // Order should be maintained (same ticket IDs in same positions)
      expect(afterClickOrder).toEqual(initialOrder);
    }
  });

});
