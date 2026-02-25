import { test, expect } from '@playwright/test';
import { authenticateAndNavigate, openTicketDrawer } from '../fixtures/helpers';

const TEST_TICKET_1 = 'TKT-024453'; // Has original + customer_reply (2 messages)
const TEST_TICKET_2 = 'TKT-023869'; // Has reply + original + multiple customer_replies (6 messages)

test.describe('Conversation Thread - No Duplicate Messages', () => {
  
  test.beforeEach(async ({ page }) => {
    await authenticateAndNavigate(page, '/all-tickets');
  });

  test('TKT-024453 shows exactly 2 messages - original appears once', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_1);
    
    // Wait for conversation to load
    await page.waitForSelector('[data-testid="message-item"]', { timeout: 10000 });
    
    // Count messages
    const messages = page.locator('[data-testid="message-item"]');
    await expect(messages).toHaveCount(2);
    
    // Verify both messages are from the same author (Hdv Hdv)
    const avatars = page.locator('[data-testid="message-avatar"]');
    await expect(avatars).toHaveCount(2);
  });

  test('TKT-023869 shows expected messages without duplicates', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_2);
    
    // Wait for conversation to load
    await page.waitForSelector('[data-testid="message-item"]', { timeout: 10000 });
    
    // Count messages - should be 6 (1 reply + 1 original + 4 customer_replies)
    const messages = page.locator('[data-testid="message-item"]');
    await expect(messages).toHaveCount(6);
  });

  test('Email source badge shows "via email" for email-originated tickets', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_1);
    
    // Check for email badge
    const emailBadge = page.locator('[data-testid="source-email-badge"]');
    await expect(emailBadge.first()).toBeVisible();
    await expect(emailBadge.first()).toContainText('via email');
  });

  test('Atlas source badge shows "via Atlas" for Atlas-originated replies', async ({ page }) => {
    await openTicketDrawer(page, TEST_TICKET_2);
    
    // Check for Atlas badge (the agent reply from Subrahmanya)
    const atlasBadge = page.locator('[data-testid="source-atlas-badge"]');
    await expect(atlasBadge.first()).toBeVisible();
    await expect(atlasBadge.first()).toContainText('via Atlas');
  });

});
