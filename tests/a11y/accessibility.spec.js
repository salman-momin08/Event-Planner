import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

async function scan(page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  return results.violations;
}

// Waits for the SPA to finish rendering a view (main always holds a focusable heading afterwards).
async function gotoView(page, hash) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`/${hash}`);
  await expect(page.locator('#main h1, #main h2').first()).toBeVisible();
}

function unique(prefix) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

test.describe('WCAG 2.2 AA — real rendered UI', () => {
  test('authentication pages have no violations', async ({ page }) => {
    await gotoView(page, '#/login');
    expect(await scan(page)).toEqual([]);
    await gotoView(page, '#/register');
    expect(await scan(page)).toEqual([]);
  });

  test('every authenticated view has no violations', async ({ page }) => {
    const email = `${unique('a11y')}@example.com`;

    // Register through the real form.
    await gotoView(page, '#/register');
    await page.getByLabel('Your name').fill('Ada Lovelace');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password').fill('correct horse battery staple');
    await page.getByRole('button', { name: 'Create account' }).click();
    await expect(page).toHaveURL(/#\/events$/);

    // Empty events list.
    await expect(page.getByRole('heading', { level: 1, name: 'Your events' })).toBeVisible();
    expect(await scan(page)).toEqual([]);

    // New-event form.
    await gotoView(page, '#/events/new');
    expect(await scan(page)).toEqual([]);

    // Create an event so the data views render populated states.
    await page.getByLabel('Event type').selectOption('wedding');
    await page.getByLabel('Title').fill('Spring Gala');
    await page.getByLabel('Event date').fill('2027-06-12');
    await page.getByLabel('Expected attendance').fill('120');
    await page.getByLabel('Location').fill('Pune');
    await page.getByLabel('Total budget').fill('25000');
    await page.getByRole('button', { name: 'Create event' }).click();
    await expect(page).toHaveURL(/#\/events\/\d+$/);

    const base = new URL(page.url()).hash.replace(/^#\//, '');
    const sections = ['', 'budget', 'tasks', 'timeline', 'vendors', 'ai', 'export'];
    for (const section of sections) {
      await gotoView(page, `#/${base}${section ? `/${section}` : ''}`);
      const violations = await scan(page);
      expect(violations, `violations on #/${base}/${section}: ${JSON.stringify(violations.map((v) => v.id))}`).toEqual([]);
    }

    // Account page (change password + delete account forms).
    await gotoView(page, '#/account');
    expect(await scan(page)).toEqual([]);
  });
});
