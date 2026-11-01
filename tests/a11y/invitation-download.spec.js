import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test.beforeEach(async ({ page }) => {
  const headers = { 'X-Requested-With': 'planner' };
  const account = await page.request.post('/api/v1/auth/register', {
    headers,
    data: {
      displayName: 'Invitation Tester',
      email: `invitation-${Date.now()}@example.com`,
      password: 'correct horse battery staple',
    },
  });
  expect(account.ok()).toBe(true);
  const response = await page.request.post('/api/v1/events', {
    headers,
    data: {
      type: 'wedding',
      title: 'Garden Gala',
      eventDate: '2027-06-12',
      attendance: 120,
      location: 'Pune',
      currency: 'INR',
      budgetCents: 2500000,
    },
  });
  expect(response.ok()).toBe(true);
  const event = await response.json();
  await page.goto(`/#/events/${event.id}/invitation`);
  await expect(page.getByRole('button', { name: 'Download High-Res PNG Card' })).toBeVisible();
});

test('invitation downloads a valid high-resolution PNG with unsaved edits', async ({ page }) => {
  await page.getByLabel('Edit main headline directly on card').fill('An unsaved celebration');

  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 });
    const downloading = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download High-Res PNG Card' }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).toBe('garden-gala-card.png');
    expect(await download.failure()).toBeNull();
    const png = await readFile(await download.path());
    expect(png.subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    expect(png.readUInt32BE(16)).toBe(1200);
    expect(png.readUInt32BE(20)).toBe(1600);
    await expect(page.getByRole('link', { name: 'Save PNG to device' })).toHaveAttribute('href', /^blob:/);
  }
});

test('a direct save link works when the browser suppresses the automatic download', async ({ page }) => {
  await page.evaluate(() => {
    HTMLAnchorElement.prototype.click = () => {};
  });
  await page.getByRole('button', { name: 'Download High-Res PNG Card' }).click();
  const saveLink = page.getByRole('link', { name: 'Save PNG to device' });
  await expect(saveLink).toBeVisible();
  await expect(page.getByText(/PNG ready\. If your download did not start/).first()).toBeVisible();
  const downloading = page.waitForEvent('download');
  await saveLink.click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe('garden-gala-card.png');
  expect(await download.failure()).toBeNull();
  const png = await readFile(await download.path());
  expect(png.readUInt32BE(16)).toBe(1200);
  expect(png.readUInt32BE(20)).toBe(1600);
});

test('failed PNG encoding reports an error and allows retrying', async ({ page }) => {
  await page.evaluate(() => {
    const original = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function (callback) {
      HTMLCanvasElement.prototype.toBlob = original;
      callback(null);
    };
  });
  const button = page.getByRole('button', { name: 'Download High-Res PNG Card' });
  await button.click();
  await expect(page.getByRole('alert')).toContainText('Could not export the invitation as a PNG.');
  await expect(page.getByRole('link', { name: 'Save PNG to device' })).toBeHidden();
  await expect(button).toBeEnabled();
  const downloading = page.waitForEvent('download');
  await button.click();
  expect(await (await downloading).failure()).toBeNull();
});

test('download resources are released when leaving the invitation studio', async ({ page }) => {
  await page.evaluate(() => {
    const original = URL.revokeObjectURL.bind(URL);
    URL.revokeObjectURL = (url) => {
      sessionStorage.setItem('releasedInvitationUrl', url);
      original(url);
    };
  });
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download High-Res PNG Card' }).click();
  await downloading;
  const url = await page.getByRole('link', { name: 'Save PNG to device' }).getAttribute('href');
  await page.getByRole('link', { name: 'Events', exact: true }).click();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('releasedInvitationUrl'))).toBe(url);
});
