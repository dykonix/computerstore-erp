import { apiRequest } from './apiClient'

export interface Supplier {
  id: number
  name: string
  contact_person: string | null
  phone: string | null
  email: string | null
  address: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SupplierListResponse {
  items: Supplier[]
  page: number
  page_size: number
  total: number
}

export interface SupplierWriteRequest {
  name: string
  contact_person: string | null
  phone: string | null
  email: string | null
  address: string | null
  is_active: boolean
}

export function fetchSuppliers(
  page = 1,
  pageSize = 100,
  isActive?: boolean,
): Promise<SupplierListResponse> {
  const activeFilter = isActive === undefined ? '' : `&is_active=${isActive}`

  return apiRequest<SupplierListResponse>(
    `/api/suppliers?page=${page}&page_size=${pageSize}${activeFilter}`,
  )
}

export function fetchSupplier(supplierId: number): Promise<Supplier> {
  return apiRequest<Supplier>(`/api/suppliers/${supplierId}`)
}

export function createSupplier(
  payload: SupplierWriteRequest,
): Promise<Supplier> {
  return apiRequest<Supplier>('/api/suppliers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSupplier(
  supplierId: number,
  payload: SupplierWriteRequest,
): Promise<Supplier> {
  return apiRequest<Supplier>(`/api/suppliers/${supplierId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}