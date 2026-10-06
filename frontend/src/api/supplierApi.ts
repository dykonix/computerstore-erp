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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
      if (typeof payload.detail === 'string') detail = payload.detail
      if (Array.isArray(payload.detail)) {
        detail = payload.detail.map((item) => item.msg ?? 'Invalid value').join(', ')
      }
    } catch {
      // Keep the status fallback when the server does not return JSON.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export function fetchSuppliers(page = 1, pageSize = 100, isActive?: boolean): Promise<SupplierListResponse> {
  const activeFilter = isActive === undefined ? '' : `&is_active=${isActive}`
  return request<SupplierListResponse>(`/api/suppliers?page=${page}&page_size=${pageSize}${activeFilter}`)
}

export function fetchSupplier(supplierId: number): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}`)
}

export function createSupplier(payload: SupplierWriteRequest): Promise<Supplier> {
  return request<Supplier>('/api/suppliers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSupplier(
  supplierId: number,
  payload: SupplierWriteRequest,
): Promise<Supplier> {
  return request<Supplier>(`/api/suppliers/${supplierId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}