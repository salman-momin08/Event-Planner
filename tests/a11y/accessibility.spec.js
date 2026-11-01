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
    const sections = ['', 'budget', 'tasks', 'timeline', 'vendors', 'decor', 'invitation', 'ai', 'export'];
    for (const section of sections) {
      await gotoView(page, `#/${base}${section ? `/${section}` : ''}`);
      const violations = await scan(page);
      expect(violations, `violations on #/${base}/${section}: ${JSON.stringify(violations.map((v) => v.id))}`).toEqual([]);
      if (section === 'invitation') {
        const card = page.locator('.invitation-card-preview');
        await expect(card).toBeVisible();
        expect(await card.evaluate((el) => getComputedStyle(el).getPropertyValue('--inv-bg').trim())).not.toBe('');
        const apiPath = `/api/v1/${base}/invitation`;
        await page.getByLabel('Edit main headline directly on card').fill('Garden Gala');
        await page.getByRole('button', { name: 'Save invitation card' }).click();
        await expect(page.getByText('Invitation card saved.', { exact: true }).first()).toBeVisible();
        const saved = await (await page.request.get(apiPath)).json();
        expect(saved.headline).toBe('Garden Gala');
        for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
          await page.setViewportSize({ width, height });
          await page.evaluate(() => window.scrollTo(0, 0));
          await expect(card).toBeVisible();
          expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
          await page.screenshot({ path: `test-results/invitation-${name}.png`, fullPage: true });
        }
        await page.setViewportSize({ width: 1280, height: 720 });
      }
    }

    // Account page (change password + delete account forms).
    await gotoView(page, '#/account');
    expect(await scan(page)).toEqual([]);
  });

  test('registration is keyboard-operable with skip link, visible focus and no traps', async ({ page }) => {
    await gotoView(page, '#/register');

    // SPA route changes move focus to the view heading (focus is managed, never lost).
    await expect(page.locator('#main h1')).toBeFocused();

    // WCAG 2.4.7: every Tab stop shows a visible focus indicator (outline or ring shadow).
    const stops = [];
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press('Tab');
      const info = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body || el.id === 'main') return null;
        const cs = getComputedStyle(el);
        return {
          label: el.getAttribute('aria-label') || el.labels?.[0]?.textContent?.trim() || el.textContent?.trim().slice(0, 40) || el.tagName,
          outline: `${cs.outlineStyle} ${cs.outlineWidth}`,
          shadow: cs.boxShadow,
        };
      });
      if (!info) break;
      stops.push(info);
    }
    expect(stops.length, 'expected at least the 3 fields, submit and switch-mode link').toBeGreaterThanOrEqual(5);
    for (const s of stops) {
      expect(s.outline.startsWith('none') && s.shadow === 'none', `no visible focus indicator on "${s.label}"`).toBe(false);
    }

    // WCAG 2.4.1: walking backwards reaches the skip link, which bypasses the header into <main>.
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Shift+Tab');
      if (await page.locator('.skip-link').evaluate((el) => el === document.activeElement)) break;
    }
    await expect(page.locator('.skip-link')).toBeFocused();
    await page.keyboard.press('Enter');
    // The router may re-render on hash change; either way focus must land inside <main>.
    expect(await page.evaluate(() => document.getElementById('main').contains(document.activeElement))).toBe(true);

    // WCAG 2.1.1: complete registration by keyboard alone (name -> email -> password -> submit).
    await gotoView(page, '#/register');
    await expect(page.locator('#main h1')).toBeFocused(); // focus lands on the heading after render
    await page.keyboard.press('Tab'); // Your name
    await expect(page.getByLabel('Your name')).toBeFocused();
    await page.keyboard.type('Ada Keys');
    await page.keyboard.press('Tab'); // Email
    await expect(page.getByLabel('Email')).toBeFocused();
    await page.keyboard.type(`${unique('kbd')}@example.com`);
    await page.keyboard.press('Tab'); // Password
    await expect(page.getByLabel('Password')).toBeFocused();
    await page.keyboard.type('correct horse battery staple');
    await page.keyboard.press('Tab'); // Create account
    await expect(page.getByRole('button', { name: 'Create account' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/#\/events$/);

    // WCAG 2.1.2: focus is never trapped — Shift+Tab walks back to the skip link.
    await expect(page.getByRole('heading', { level: 1, name: 'Your events' })).toBeVisible();
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press('Shift+Tab');
      if (await page.locator('.skip-link').evaluate((el) => el === document.activeElement)) break;
    }
    await expect(page.locator('.skip-link')).toBeFocused();
  });
});
