import { expect, test } from '@playwright/test'

/**
 * Verifies the dashboard renders the exact data seeded by
 * backend/scripts/seed_trading_sample_data.py for the `testuser` account.
 * That script refuses to run a second time once a user has any orders, so
 * this fixed data is stable for the lifetime of this local database — if
 * the seed is ever re-run against a fresh DB for a different user, update
 * TEST_USERNAME/TEST_PASSWORD below to match.
 */

const TEST_USERNAME = 'testuser'
const TEST_PASSWORD = 'correct horse battery staple'

test.beforeEach(async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username or email').fill(TEST_USERNAME)
  await page.getByLabel('Password').fill(TEST_PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  // Let the four parallel dashboard fetches settle.
  await expect(page.getByText('Open positions', { exact: true })).toBeVisible()
})

test('summary cards show the seeded totals', async ({ page }) => {
  const cards = page.locator('.summary-card')
  await expect(cards).toHaveCount(5)

  await expect(page.locator('.summary-card', { hasText: 'Open positions' })).toContainText('1')
  await expect(page.locator('.summary-card', { hasText: 'Open orders' })).toContainText('1')
  // Regex, anchored + case-sensitive: a plain string filter here is
  // case-insensitive substring matching, so 'Realized PnL' would also match
  // the "Unrealized PnL" card.
  await expect(
    page.locator('.summary-card', { hasText: /^Unrealized PnL/ }),
  ).toContainText('600.00')
  await expect(page.locator('.summary-card', { hasText: 'Closed trades' })).toContainText('2')
  await expect(page.locator('.summary-card', { hasText: /^Realized PnL/ })).toContainText(
    '97.80',
  )
})

test('positions table shows the open BTC/USD position', async ({ page }) => {
  const section = page.locator('.dashboard-section', { hasText: 'Positions' })
  const row = section.locator('tbody tr')
  await expect(row).toHaveCount(1)
  await expect(row).toContainText('BTC/USD')
  await expect(row).toContainText('long')
  await expect(row).toContainText('open')
})

test('orders table shows all three seeded orders', async ({ page }) => {
  const section = page.locator('.dashboard-section', { hasText: 'Orders' }).first()
  const rows = section.locator('tbody tr')
  await expect(rows).toHaveCount(3)
  await expect(rows.filter({ hasText: 'ETH/USD' })).toContainText('open')
  await expect(rows.filter({ hasText: 'BTC/USD' }).filter({ hasText: 'buy' })).toContainText(
    'filled',
  )
  await expect(rows.filter({ hasText: 'BTC/USD' }).filter({ hasText: 'sell' })).toContainText(
    'filled',
  )
})

test('executions table shows both fills', async ({ page }) => {
  const section = page.locator('.dashboard-section', { hasText: 'Recent executions' })
  const rows = section.locator('tbody tr')
  await expect(rows).toHaveCount(2)
  await expect(rows.filter({ hasText: '61,000.00' })).toBeVisible()
  await expect(rows.filter({ hasText: '60,000.00' })).toBeVisible()
})

test('trades table shows the winner and the loser with correct signs', async ({ page }) => {
  const section = page.locator('.dashboard-section', { hasText: 'Recent trades' })
  const rows = section.locator('tbody tr')
  await expect(rows).toHaveCount(2)

  const winner = rows.filter({ hasText: 'BTC/USD' })
  await expect(winner).toContainText('198.80')
  await expect(winner.locator('td.positive')).toHaveCount(2) // net PnL + return %

  const loser = rows.filter({ hasText: 'ETH/USD' })
  await expect(loser).toContainText('-101.00')
  await expect(loser.locator('td.negative')).toHaveCount(2)
})

test('refresh re-fetches without navigating away', async ({ page }) => {
  await page.getByRole('button', { name: 'Refresh' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.locator('.summary-card', { hasText: 'Open positions' })).toContainText('1')
})
