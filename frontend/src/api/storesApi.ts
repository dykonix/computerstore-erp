import { apiRequest } from './apiClient'

export interface Store {
  id: number
  name: string
  address: string | null
  is_active: boolean
}

export function fetchAllowedStores(): Promise<Store[]> {
  return apiRequest<Store[]>('/api/stores')
}