import { expect, test } from '@playwright/test'

/**
 * Covers the login + protected-dashboard mechanics in isolation from any
 * fixed seed data: each test that needs an authenticated user registers a
 * fresh, uniquely-named one via the API first, so this suite never depends
 * on (or mutates) the shared `testuser` account used in dashboard.spec.ts.
 */

interface TestAccount {
  username: string
  email: string
  password: string
}

function freshAccount(): TestAccount {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 1e6)}`
  return {
    username: `e2e_${suffix}`.slice(0, 50),
    email: `e2e_${suffix}@example.com`,
    password: 'correct horse battery staple',
  }
}

test.describe('unauthenticated access', () => {
  test('redirects the root route to /login', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  })
})

test.describe('login', () => {
  test('rejects wrong credentials with a visible error, no navigation', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Username or email').fill('no-such-user')
    await page.getByLabel('Password').fill('definitely-wrong-password')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.locator('.auth-error')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test.describe('registration flow (isolated E2E backend)', () => {
    // This test writes a new, permanent user row on every run. Routed at the
    // isolated backend (:8001 -> ali_trading_e2e, a database dedicated to
    // this path — see backend/.env.e2e), never the real dev backend
    // (:8000 -> ali_trading) that every other test in this file uses via
    // the default baseURL from playwright.config.ts.
    test.use({ baseURL: 'http://localhost:5174' })

    test('registers, logs in, reaches the protected dashboard, and logs out', async ({
      page,
      request,
    }) => {
      const account = freshAccount()

      const registerResponse = await request.post('/api/auth/register', {
        data: {
          email: account.email,
          username: account.username,
          password: account.password,
        },
      })
      expect(registerResponse.ok()).toBe(true)

      await page.goto('/login')
      await page.getByLabel('Username or email').fill(account.username)
      await page.getByLabel('Password').fill(account.password)
      await page.getByRole('button', { name: 'Sign in' }).click()

      await expect(page).toHaveURL('http://localhost:5174/')
      await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
      await expect(page.getByText(`Welcome, ${account.username}.`)).toBeVisible()

      // A brand-new user has no trading data — dashboard should render the
      // empty state cleanly, not error out. exact:true avoids matching inside
      // the "No open positions." empty-state text below (getByText does
      // substring matching by default).
      await expect(page.getByText('Open positions', { exact: true })).toBeVisible()
      await expect(page.getByText('No open positions.')).toBeVisible()
      await expect(page.getByText('No orders yet.')).toBeVisible()

      await page.getByRole('button', { name: 'Sign out' }).click()
      await expect(page).toHaveURL(/\/login$/)

      // Signing out must actually revoke the session client-side: going back
      // to "/" should bounce to /login again, not show stale dashboard state.
      await page.goto('/')
      await expect(page).toHaveURL(/\/login$/)
    })
  })
})

test.describe('session expiry while the dashboard is open', () => {
  // This test writes a new, permanent user row on every run — routed at the
  // isolated E2E backend (:8001 -> ali_trading_e2e), same as the
  // "registration flow" block above, never the real dev backend (:8000 ->
  // ali_trading).
  test.use({ baseURL: 'http://localhost:5174' })

  // Regression coverage for the Phase 7.5 bug: when both the access and
  // refresh tokens are invalid/revoked, client.ts's apiRequest() used to
  // clear its own module-level tokens and rethrow, but AuthContext's `user`
  // state was never cleared — so ProtectedRoute never redirected and the
  // dashboard stayed mounted showing only an API error banner. This forces
  // that exact "both tokens invalid" condition deterministically via route
  // interception (real token TTLs are minutes/hours, not test-friendly) and
  // asserts the app now redirects to /login instead.
  test('redirects to /login once a background refresh fails, instead of leaving a stale dashboard visible', async ({
    page,
  }) => {
    const account = freshAccount()
    const registerResponse = await page.request.post('/api/auth/register', {
      data: { email: account.email, username: account.username, password: account.password },
    })
    expect(registerResponse.ok()).toBe(true)

    await page.goto('/login')
    await page.getByLabel('Username or email').fill(account.username)
    await page.getByLabel('Password').fill(account.password)
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('Open positions', { exact: true })).toBeVisible()

    // Simulate both tokens being invalid/revoked: every authenticated
    // trading call now 401s, and the refresh attempt it triggers 401s too.
    await page.route('**/api/trading/**', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'unauthorized', message: 'Token invalid.' } }),
      }),
    )
    await page.route('**/api/auth/refresh', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'unauthorized', message: 'Refresh token invalid.' } }),
      }),
    )

    await page.getByRole('button', { name: 'Refresh' }).click()

    await expect(page).toHaveURL(/\/login$/)
  })
})
