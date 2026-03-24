import { Page, expect } from '@playwright/test';

const BASE_URL = 'https://docs-sync-test.preview.emergentagent.com';
const SESSION_TOKEN = 'playwright_test_session';

export async function authenticateAndNavigate(page: Page, path: string = '/all-tickets') {
  // Set session cookie for authentication
  await page.context().addCookies([{
    name: 'session_token',
    value: SESSION_TOKEN,
    domain: 'kb-management-hub.preview.emergentagent.com',
    path: '/',
    httpOnly: true,
    secure: true,
    sameSite: 'None'
  }]);

  await page.goto(path, { waitUntil: 'domcontentloaded' });
}

export async function waitForAppReady(page: Page) {
  await page.waitForLoadState('domcontentloaded');
}

export async function dismissToasts(page: Page) {
  await page.addLocatorHandler(
    page.locator('[data-sonner-toast], .Toastify__toast, [role="status"].toast, .MuiSnackbar-root'),
    async () => {
      const close = page.locator('[data-sonner-toast] [data-close], [data-sonner-toast] button[aria-label="Close"], .Toastify__close-button, .MuiSnackbar-root button');
      await close.first().click({ timeout: 2000 }).catch(() => {});
    },
    { times: 10, noWaitAfter: true }
  );
}

export async function openTicketDrawer(page: Page, ticketId: string) {
  await page.goto(`/all-tickets?ticket=${ticketId}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="ticket-drawer"]', { timeout: 15000 });
}

export async function checkForErrors(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const errorElements = Array.from(
      document.querySelectorAll('.error, [class*="error"], [id*="error"]')
    );
    return errorElements.map(el => el.textContent || '').filter(Boolean);
  });
}
