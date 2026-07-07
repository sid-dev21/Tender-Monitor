import { api } from './client'

export interface HealthStatus {
  status: string
  mongo: string
}

// Calls the backend /health endpoint — used by the layout to show a live
// "backend connected" badge, proving the frontend<->backend link works.
export async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await api.get<HealthStatus>('/health')
  return data
}
