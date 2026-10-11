import { apiRequest } from './apiClient'

export interface SaleItemResponse {
  id: number
  sale_id: number
  product_id: number
  quantity: number
  configured_unit_price: number
  configured_minimum_price: number
  actual_unit_price: number
  minimum_price_override: boolean
  is_free_product: boolean
  promotion_id: number | null
  promotion_name: string | null
  promotion_cashback_amount: number
  promotion_benefit_id: number | null
  promotion_benefit_name: string | null
  promotion_source_sale_item_id: number | null
  is_promotion_benefit: boolean
  promotion_benefit_source: string | null
  serial_numbers: string[]
  requires_serial_number: boolean
  cost_price: number
  gst_rate: number
  gst_amount: number
  discount_amount: number
  line_total: number
}

export interface SaleResponse {
  id: number
  tenant_id: number
  store_id: number
  customer_id: number | null
  employee_id: number
  status: string
  cashback_amount: number
  subtotal: number
  invoice_discount: number
  taxable_amount: number
  gst_amount: number
  total_amount: number
  payable_amount: number
  reserved_at: string | null
  reservation_warning_at: string | null
  reservation_expires_at: string | null
  items: SaleItemResponse[]
}

export interface CreateSaleRequest {
  store_id: number
  customer_id: number | null
}

export interface AddSaleItemRequest {
  product_id: number
  quantity: number
  actual_unit_price?: number
  configured_minimum_price?: number
  minimum_price_override?: boolean
  is_free_product?: boolean
  promotion_id?: number | null
  promotion_benefit_ids?: number[]
  promotion_benefit_ids_by_unit?: number[][]
  promotion_benefit_sources_by_unit?: Record<number, 'STORE' | 'MANUFACTURER'>[]
}

export interface SaleDeliveryRequest {
  serial_numbers_by_item: Record<number, string[]>
  allow_missing_serial_numbers: boolean
}

export interface SalePaymentRequest {
  payment_mode: string
  amount: number
  transaction_reference?: string | null
}

export interface SalePaymentResponse extends SalePaymentRequest {
  id: number
  sale_id: number
  payment_mode: string
  amount: number
  transaction_reference: string | null
  paid_at: string
}

export async function createSale(
  request: CreateSaleRequest,
): Promise<SaleResponse> {
  return apiRequest<SaleResponse>('/api/sales', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function fetchSale(
  saleId: number,
): Promise<SaleResponse> {
  return apiRequest<SaleResponse>(
    `/api/sales/${saleId}`,
  )
}

export interface LocationAvailability {
  location_type: string
  location_name: string
  quantity: number
  reserved_quantity: number
  available_quantity: number
}

export interface ProductAvailability {
  current_store: LocationAvailability
  other_locations: LocationAvailability[]
}

export async function fetchProductAvailability(
  productId: number,
  storeId: number,
): Promise<ProductAvailability> {
  return apiRequest<ProductAvailability>(
    `/api/sales/availability/${productId}?store_id=${storeId}`,
  )
}

export async function addSaleItem(
  saleId: number,
  request: AddSaleItemRequest,
): Promise<SaleItemResponse> {
  return apiRequest<SaleItemResponse>(
    `/api/sales/${saleId}/items`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  )
}

export async function reserveSale(
  saleId: number,
): Promise<SaleResponse> {
  return apiRequest<SaleResponse>(
    `/api/sales/${saleId}/reserve`,
    {
      method: 'POST',
    },
  )
}

export async function fetchSalePayments(
  saleId: number,
): Promise<SalePaymentResponse[]> {
  return apiRequest<SalePaymentResponse[]>(
    `/api/sales/${saleId}/payments`,
  )
}

export async function addSalePayment(
  saleId: number,
  request: SalePaymentRequest,
): Promise<SalePaymentResponse> {
  return apiRequest<SalePaymentResponse>(
    `/api/sales/${saleId}/payments`,
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  )
}

export async function confirmSale(
  saleId: number,
): Promise<SaleResponse> {
  return apiRequest<SaleResponse>(
    `/api/sales/${saleId}/confirm`,
    {
      method: 'POST',
    },
  )
}

export async function deliverSale(
  saleId: number,
  request?: SaleDeliveryRequest,
): Promise<SaleResponse> {
  return apiRequest<SaleResponse>(
    `/api/sales/${saleId}/deliver`,
    {
      method: 'POST',
      body: request ? JSON.stringify(request) : undefined,
    },
  )
}