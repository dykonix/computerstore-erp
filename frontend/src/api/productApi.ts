export type DataType = 'SELECT' | 'MULTI_SELECT' | 'NUMBER' | 'DECIMAL' | 'TEXT'

export interface Category {
  id: number
  name: string
}

export interface Brand {
  id: number
  name: string
}

export interface Attribute {
  id: number
  name: string
  data_type: DataType
  unit: string | null
}

export interface AttributeOption {
  id: number
  attribute_id: number
  value: string
  display_order: number
}

export interface CategoryAttribute {
  category_id: number
  attribute_id: number
  is_required: boolean
  display_order: number
}

export interface ProductFormData {
  categories: Category[]
  brands: Brand[]
  attributes: Attribute[]
  attribute_options: AttributeOption[]
  category_attributes: CategoryAttribute[]
}

export interface ProductListItem {
  id: number
  sku: string
  name: string
  category: Category
  brand: Brand
  is_active: boolean
}

export interface ProductListResponse {
  items: ProductListItem[]
  page: number
  page_size: number
  total: number
}

export interface ProductAttributeValueResponse {
  id: number
  attribute_id: number
  attribute_name: string
  data_type: DataType
  unit: string | null
  attribute_option_id: number | null
  attribute_option_value: string | null
  text_value: string | null
  number_value: number | null
  decimal_value: number | null
}

export interface ProductResponse extends ProductListItem {
  description: string | null
  attributes: ProductAttributeValueResponse[]
}

export interface ProductAttributeValueCreate {
  attribute_id: number
  attribute_option_id?: number
  text_value?: string
  number_value?: number
  decimal_value?: number
}

export interface ProductCreateRequest {
  sku: string
  name: string
  category_id: number
  brand_id: number
  description?: string
  is_active: boolean
  attributes: ProductAttributeValueCreate[]
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
      // Keep the useful status fallback when the server returns a non-JSON error.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export function fetchProductFormData(): Promise<ProductFormData> {
  return request<ProductFormData>('/api/products/form-data')
}

export function fetchProducts(): Promise<ProductListResponse> {
  return request<ProductListResponse>('/api/products?page=1&page_size=100')
}

export function createProduct(payload: ProductCreateRequest): Promise<ProductResponse> {
  return request<ProductResponse>('/api/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchProduct(productId: number): Promise<ProductResponse> {
  return request<ProductResponse>(`/api/products/${productId}`)
}

export function updateProduct(
  productId: number,
  payload: ProductCreateRequest,
): Promise<ProductResponse> {
  return request<ProductResponse>(`/api/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}