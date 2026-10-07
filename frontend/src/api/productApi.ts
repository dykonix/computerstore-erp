import { apiRequest } from './apiClient'

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

export interface ProductPriceResponse {
  id: number
  product_id: number
  sale_price: number
  minimum_sale_price: number | null
  valid_from: string
  valid_to: string | null
  created_at: string
  updated_at: string
}

export interface ProductPriceWriteRequest {
  sale_price: number
  minimum_sale_price: number | null
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

export function fetchProductFormData(): Promise<ProductFormData> {
  return apiRequest<ProductFormData>('/api/products/form-data')
}

export function fetchProducts(): Promise<ProductListResponse> {
  return apiRequest<ProductListResponse>('/api/products?page=1&page_size=100')
}

export function createProduct(
  payload: ProductCreateRequest,
): Promise<ProductResponse> {
  return apiRequest<ProductResponse>('/api/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchProduct(productId: number): Promise<ProductResponse> {
  return apiRequest<ProductResponse>(`/api/products/${productId}`)
}

export function updateProduct(
  productId: number,
  payload: ProductCreateRequest,
): Promise<ProductResponse> {
  return apiRequest<ProductResponse>(`/api/products/${productId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function fetchCurrentProductPrice(
  productId: number,
): Promise<ProductPriceResponse | null> {
  try {
    return await apiRequest<ProductPriceResponse>(
      `/api/products/${productId}/prices/current`,
    )
  } catch (error) {
    if (error instanceof Error && error.message === 'Current product price not found') {
      return null
    }
    throw error
  }
}

export function createProductPrice(
  productId: number,
  payload: ProductPriceWriteRequest,
): Promise<ProductPriceResponse> {
  return apiRequest<ProductPriceResponse>(`/api/products/${productId}/prices`, {
    method: 'POST',
    body: JSON.stringify({ ...payload, valid_from: new Date().toISOString().slice(0, 10) }),
  })
}

export function updateProductPrice(
  productId: number,
  priceId: number,
  payload: ProductPriceWriteRequest,
): Promise<ProductPriceResponse> {
  return apiRequest<ProductPriceResponse>(
    `/api/products/${productId}/prices/${priceId}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
  )
}