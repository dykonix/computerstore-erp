export interface WarrantyOption {
  id: number
  product_id: number
  additional_months: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WarrantyOptionWriteRequest {
  product_id: number
  additional_months: number
}

export interface WarrantyOptionUpdateRequest {
  additional_months: number
}

export interface WarrantyPrice {
  id: number
  warranty_option_id: number
  price: number
  valid_from: string
  valid_to: string | null
  created_at: string
  updated_at: string
}

export interface WarrantyPriceWriteRequest {
  price: number
  valid_from: string
  valid_to: string | null
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
      // Keep the status fallback when the server returns a non-JSON error.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export function fetchWarrantyOptions(
  productId: number,
  page = 1,
  pageSize = 100,
): Promise<WarrantyOption[]> {
  return request<WarrantyOption[]>(
    `/api/warranty-options?product_id=${productId}&page=${page}&page_size=${pageSize}`,
  )
}

export function fetchWarrantyOption(optionId: number): Promise<WarrantyOption> {
  return request<WarrantyOption>(`/api/warranty-options/${optionId}`)
}

export function createWarrantyOption(
  payload: WarrantyOptionWriteRequest,
): Promise<WarrantyOption> {
  return request<WarrantyOption>('/api/warranty-options', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateWarrantyOption(
  optionId: number,
  payload: WarrantyOptionUpdateRequest,
): Promise<WarrantyOption> {
  return request<WarrantyOption>(`/api/warranty-options/${optionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function setWarrantyOptionStatus(
  optionId: number,
  isActive: boolean,
): Promise<WarrantyOption> {
  return request<WarrantyOption>(
    `/api/warranty-options/${optionId}/status?is_active=${isActive}`,
    { method: 'PATCH' },
  )
}

export function fetchWarrantyPrices(optionId: number): Promise<WarrantyPrice[]> {
  return request<WarrantyPrice[]>(`/api/warranty-options/${optionId}/prices`)
}

export function createWarrantyPrice(
  optionId: number,
  payload: WarrantyPriceWriteRequest,
): Promise<WarrantyPrice> {
  return request<WarrantyPrice>(`/api/warranty-options/${optionId}/prices`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateWarrantyPrice(
  priceId: number,
  payload: WarrantyPriceWriteRequest,
): Promise<WarrantyPrice> {
  return request<WarrantyPrice>(`/api/warranty-options/prices/${priceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}