import { api } from './client'

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserProfile {
  id: string
  email: string
  company_profile: string | null
  keywords: string[]
  notification_emails: string[]
  in_app_notifications_enabled: boolean
  is_active: boolean
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>('/api/auth/login', { email, password })
  return data
}

export async function register(email: string, password: string): Promise<UserProfile> {
  const { data } = await api.post<UserProfile>('/api/auth/register', { email, password })
  return data
}

export async function fetchMe(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>('/api/users/me')
  return data
}

/** Request a reset link. Always resolves (server returns 202 whether or not the
 * email exists) — the UI must not reveal which. */
export async function forgotPassword(email: string): Promise<void> {
  await api.post('/api/auth/forgot-password', { email })
}

/** Consume a reset token, set a new password, and receive fresh tokens. */
export async function resetPassword(token: string, newPassword: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>('/api/auth/reset-password', {
    token,
    new_password: newPassword,
  })
  return data
}
