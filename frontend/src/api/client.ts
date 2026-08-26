const API_BASE = '/api'

export class ApiError extends Error {
  status: number
  code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

let accessToken: string | null = null
let refreshToken: string | null = null
let pendingRefresh: Promise<void> | null = null

export function setTokens(tokens: { accessToken: string; refreshToken: string } | null): void {
  accessToken = tokens?.accessToken ?? null
  refreshToken = tokens?.refreshToken ?? null
}

export function getRefreshToken(): string | null {
  return refreshToken
}

type SessionExpiredListener = () => void
let sessionExpiredListeners: SessionExpiredListener[] = []

/**
 * Notified when a background token refresh fails (both access and refresh
 * tokens invalid/revoked) — the only way anything outside this module learns
 * that `setTokens(null)` just happened for that reason, not from an explicit
 * logout() call. AuthContext uses this to clear its `user` state so
 * ProtectedRoute redirects to /login instead of leaving a stale dashboard
 * mounted with just an API error.
 */
export function onSessionExpired(listener: SessionExpiredListener): () => void {
  sessionExpiredListeners.push(listener)
  return () => {
    sessionExpiredListeners = sessionExpiredListeners.filter((l) => l !== listener)
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  auth?: boolean
}

async function parseErrorBody(res: Response): Promise<ApiError> {
  let message = res.statusText || `Request failed with status ${res.status}`
  let code: string | undefined
  try {
    const data = (await res.json()) as { error?: { code?: string; message?: string } }
    if (data.error?.message) message = data.error.message
    code = data.error?.code
  } catch {
    // Response body wasn't JSON — fall back to statusText.
  }
  return new ApiError(res.status, message, code)
}

async function rawRequest<T>(path: string, options: RequestOptions): Promise<T> {
  const { method = 'GET', body, auth = false } = options
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 204) return undefined as T
  if (!res.ok) throw await parseErrorBody(res)
  return (await res.json()) as T
}

async function refreshAccessToken(): Promise<void> {
  if (!refreshToken) throw new ApiError(401, 'No refresh token available.')
  const result = await rawRequest<{ access_token: string; refresh_token: string }>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
  })
  accessToken = result.access_token
  refreshToken = result.refresh_token
}

/**
 * On a 401 from an `auth: true` call, attempts one refresh-and-retry before
 * giving up and clearing tokens — callers only ever see the original error.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  try {
    return await rawRequest<T>(path, options)
  } catch (err) {
    if (!options.auth || !(err instanceof ApiError) || err.status !== 401) throw err

    pendingRefresh ??= refreshAccessToken().finally(() => {
      pendingRefresh = null
    })
    try {
      await pendingRefresh
    } catch {
      setTokens(null)
      sessionExpiredListeners.forEach((listener) => listener())
      throw err
    }
    return rawRequest<T>(path, options)
  }
}
