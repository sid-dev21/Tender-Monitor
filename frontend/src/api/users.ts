import { api } from './client'
import type { UserProfile } from './auth'

export async function updateKeywords(keywords: string[]): Promise<UserProfile> {
  const { data } = await api.patch<UserProfile>('/api/users/me/keywords', { keywords })
  return data
}

export async function updateNotificationEmails(emails: string[]): Promise<UserProfile> {
  const { data } = await api.patch<UserProfile>('/api/users/me/notification-emails', { emails })
  return data
}

export async function updateCompanyProfile(companyProfile: string): Promise<UserProfile> {
  const { data } = await api.patch<UserProfile>('/api/users/me/profile', {
    company_profile: companyProfile,
  })
  return data
}
