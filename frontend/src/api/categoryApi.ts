export interface Category {
  id: number
  name: string
  description: string | null
  gst_rate: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CategoryWriteRequest {
  name: string
  description?: string | null
  gst_rate?: number | null
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
      // Keep the status fallback for non-JSON errors.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export function fetchCategories(page = 1, pageSize = 100): Promise<Category[]> {
  return request<Category[]>(`/api/categories?page=${page}&page_size=${pageSize}`)
}

export function fetchCategory(categoryId: number): Promise<Category> {
  return request<Category>(`/api/categories/${categoryId}`)
}

export function createCategory(payload: CategoryWriteRequest): Promise<Category> {
  return request<Category>('/api/categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateCategory(
  categoryId: number,
  payload: CategoryWriteRequest,
): Promise<Category> {
  return request<Category>(`/api/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function setCategoryStatus(
  categoryId: number,
  isActive: boolean,
): Promise<Category> {
  return request<Category>(
    `/api/categories/${categoryId}/status?is_active=${isActive}`,
    { method: 'PATCH' },
  )
}