import { apiRequest } from './apiClient'

export interface InventoryProduct {
  id: number
  name: string
  sku: string
}

export interface InventoryLocation {
  id: number
  name: string
}

export interface InventoryFormData {
  products: InventoryProduct[]
  stores: InventoryLocation[]
  godowns: InventoryLocation[]
}

export interface InventoryItem {
  id: number
  product_id: number
  store_id: number | null
  godown_id: number | null
  product_name: string
  sku: string
  brand: string
  category: string
  location: {
    type: string
    name: string
  }
  quantity: number
  reserved_quantity: number
  available_quantity: number
  cost_price: number
}

export interface InventoryListResponse {
  items: InventoryItem[]
  page: number
  page_size: number
  total: number
}

export interface OpeningStockRequest {
  product_id: number
  supplier_id: number
  store_id?: number
  godown_id?: number
  quantity: number
  cost_price: number
}

export interface InventoryTransferRequest {
  product_id: number
  source_store_id: number | null
  source_godown_id: number | null
  destination_store_id: number | null
  destination_godown_id: number | null
  quantity: number
}

export function fetchInventoryFormData(): Promise<InventoryFormData> {
  return apiRequest<InventoryFormData>('/api/inventory/form-data')
}

export function fetchInventory(
  productId?: number,
  storeId?: number,
): Promise<InventoryListResponse> {
  const query = new URLSearchParams({ page: '1', page_size: '100' })
  if (productId !== undefined) query.set('product_id', String(productId))
  if (storeId !== undefined) query.set('store_id', String(storeId))
  return apiRequest<InventoryListResponse>(`/api/inventory?${query}`)
}

export function createOpeningStock(
  payload: OpeningStockRequest,
): Promise<InventoryItem> {
  return apiRequest<InventoryItem>('/api/inventory/opening', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function transferInventory(
  payload: InventoryTransferRequest,
): Promise<InventoryItem> {
  return apiRequest<InventoryItem>('/api/inventory/transfer', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateInventoryCostPrice(
  inventoryId: number,
  costPrice: number,
): Promise<InventoryItem> {
  return apiRequest<InventoryItem>(`/api/inventory/${inventoryId}`, {
    method: 'PUT',
    body: JSON.stringify({ cost_price: costPrice }),
  })
}