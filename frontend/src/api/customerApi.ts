import { apiRequest } from './apiClient'

export interface Customer {
  id: number
  name: string
  mobile: string | null
  email: string | null
  address: string | null
  is_active: boolean
}

export interface CustomerCreateRequest {
  name: string
  mobile: string
  email?: string | null
  address?: string | null
}

export function fetchCustomers(): Promise<Customer[]> {
  return apiRequest<Customer[]>('/api/customers')
}

export function searchCustomers(query: string): Promise<Customer[]> {
  return apiRequest<Customer[]>(`/api/customers/search?query=${encodeURIComponent(query)}`)
}

export function createCustomer(payload: CustomerCreateRequest): Promise<Customer> {
  return apiRequest<Customer>('/api/customers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}