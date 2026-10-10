import { apiRequest } from './apiClient'

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

export function fetchCategories(
  page = 1,
  pageSize = 100,
): Promise<Category[]> {
  return apiRequest<Category[]>(
    `/api/categories?page=${page}&page_size=${pageSize}`,
  )
}

export function fetchCategory(categoryId: number): Promise<Category> {
  return apiRequest<Category>(`/api/categories/${categoryId}`)
}

export function createCategory(
  payload: CategoryWriteRequest,
): Promise<Category> {
  return apiRequest<Category>('/api/categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateCategory(
  categoryId: number,
  payload: CategoryWriteRequest,
): Promise<Category> {
  return apiRequest<Category>(`/api/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function setCategoryStatus(
  categoryId: number,
  isActive: boolean,
): Promise<Category> {
  return apiRequest<Category>(
    `/api/categories/${categoryId}/status?is_active=${isActive}`,
    {
      method: 'PATCH',
    },
  )
}