// Agent-tooling driver for the run-ali-trading-dashboard skill.
//
// Drives the real frontend dev server (assumed already running at
// FRONTEND_URL, default http://localhost:5173, proxying /api to the
// backend) through a login + dashboard-load flow using headless Chromium
// (via `playwright`), and writes screenshots + a text summary to
// ./screenshots/ next to this file.
//
// Usage (from this directory, after `npm install` + `npx playwright
// install chromium` once):
//   node driver.mjs
//
// Env overrides:
//   FRONTEND_URL   default http://localhost:5173
//   TEST_USERNAME  default testuser
//   TEST_PASSWORD  default "correct horse battery staple"

import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = join(HERE, 'screenshots');
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const FRONTEND_URL = process.env.FRONTEND_URL ?? 'http://localhost:5173';
const USERNAME = process.env.TEST_USERNAME ?? 'testuser';
const PASSWORD = process.env.TEST_PASSWORD ?? 'correct horse battery staple';

async function main() {
  const consoleErrors = [];
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(String(err)));

  await page.goto(FRONTEND_URL, { waitUntil: 'networkidle' });
  await page.waitForSelector('text=Sign in', { timeout: 15000 });
  await page.screenshot({ path: join(SCREENSHOT_DIR, 'login.png') });

  await page.fill('input[autocomplete="username"]', USERNAME);
  await page.fill('input[autocomplete="current-password"]', PASSWORD);
  await page.click('button[type="submit"]');

  await page.waitForSelector('text=Dashboard', { timeout: 15000 });
  await page.waitForSelector('text=Recent trades', { timeout: 15000 });
  // Let the four parallel dashboard fetches (summary/positions/orders/
  // executions/trades) settle onto the page after the section headers render.
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(SCREENSHOT_DIR, 'dashboard.png'), fullPage: true });

  const bodyText = (await page.textContent('body')).replace(/\s+/g, ' ').trim();

  console.log('--- CONSOLE ERRORS ---');
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(none)');
  console.log('--- BODY TEXT SNIPPET (first 1000 chars) ---');
  console.log(bodyText.slice(0, 1000));
  console.log('--- SCREENSHOTS ---');
  console.log(join(SCREENSHOT_DIR, 'login.png'));
  console.log(join(SCREENSHOT_DIR, 'dashboard.png'));

  await browser.close();

  if (consoleErrors.length > 0) {
    console.error('FAILED: console errors were logged during the run.');
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('DRIVER FAILED:', err);
  process.exit(1);
});
