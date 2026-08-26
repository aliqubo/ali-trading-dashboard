import { apiRequest, getRefreshToken, setTokens } from './client'

export interface User {
  id: string
  email: string
  username: string
  full_name: string | null
  phone: string | null
  status: string
  is_email_verified: boolean
  two_factor_enabled: boolean
  locale: string
  timezone: string
  created_at: string
  updated_at: string
}

export interface Role {
  id: string
  name: string
  display_name: string
  description: string | null
  is_system: boolean
  created_at: string
}

export interface Permission {
  id: string
  code: string
  resource: string
  action: string
  description: string | null
}

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface MeResponse {
  user: User
  roles: Role[]
  permissions: Permission[]
}

export async function register(input: {
  email: string
  username: string
  password: string
  full_name?: string
}): Promise<User> {
  return apiRequest<User>('/auth/register', { method: 'POST', body: input })
}

export async function login(identifier: string, password: string): Promise<User> {
  const result = await apiRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: { identifier, password },
  })
  setTokens({ accessToken: result.access_token, refreshToken: result.refresh_token })
  return result.user
}

export async function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>('/auth/me', { auth: true })
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken()
  setTokens(null)
  if (refreshToken) {
    await apiRequest<void>('/auth/logout', { method: 'POST', body: { refresh_token: refreshToken } })
  }
}
