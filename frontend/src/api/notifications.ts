import { api } from './client'

export interface InAppNotification {
  id: string
  tender_ids: string[]
  seen: boolean
  created_at: string
}

export interface SendNowResult {
  sent: boolean
  count: number
  emailed: boolean
}

export interface Schedule {
  frequency: 'daily' | 'weekly'
  time: string
  timezone: string
  is_active: boolean
  last_sent_at: string | null
}

export async function listNotifications(): Promise<InAppNotification[]> {
  const { data } = await api.get<InAppNotification[]>('/api/notifications')
  return data
}

export async function markSeen(id: string): Promise<void> {
  await api.patch(`/api/notifications/${id}/mark-seen`)
}

export async function sendNow(): Promise<SendNowResult> {
  const { data } = await api.post<SendNowResult>('/api/notifications/send-now')
  return data
}

export async function getSchedule(): Promise<Schedule | null> {
  try {
    const { data } = await api.get<Schedule>('/api/notification-schedule')
    return data
  } catch {
    return null // 404 when not yet configured
  }
}

export async function setSchedule(body: {
  frequency: 'daily' | 'weekly'
  time: string
  timezone: string
}): Promise<Schedule> {
  const { data } = await api.post<Schedule>('/api/notification-schedule', body)
  return data
}
