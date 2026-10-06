export interface InventoryProduct { id: number; name: string; sku: string }
export interface InventoryLocation { id: number; name: string }
export interface InventoryFormData { products: InventoryProduct[]; stores: InventoryLocation[]; godowns: InventoryLocation[] }
export interface InventoryItem {
  id: number; product_id: number; product_name: string; sku: string; brand: string; category: string
  location: { type: string; name: string }; quantity: number; reserved_quantity: number; available_quantity: number
}
export interface InventoryListResponse { items: InventoryItem[]; page: number; page_size: number; total: number }
export interface OpeningStockRequest { product_id: number; supplier_id: number; store_id?: number; godown_id?: number; quantity: number }
export interface InventoryTransferRequest {
  product_id: number
  source_store_id: number | null
  source_godown_id: number | null
  destination_store_id: number | null
  destination_godown_id: number | null
  quantity: number
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...options?.headers }, ...options })
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const payload = await response.json() as { detail?: string | Array<{ msg?: string }> }
      if (typeof payload.detail === 'string') detail = payload.detail
      if (Array.isArray(payload.detail)) detail = payload.detail.map((item) => item.msg ?? 'Invalid value').join(', ')
    } catch { /* Use the status fallback for non-JSON errors. */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export function fetchInventoryFormData(): Promise<InventoryFormData> { return request('/api/inventory/form-data') }
export function fetchInventory(): Promise<InventoryListResponse> { return request('/api/inventory?page=1&page_size=100') }
export function createOpeningStock(payload: OpeningStockRequest): Promise<InventoryItem> {
  return request('/api/inventory/opening', { method: 'POST', body: JSON.stringify(payload) })
}
export function transferInventory(payload: InventoryTransferRequest): Promise<InventoryItem> {
  return request('/api/inventory/transfer', { method: 'POST', body: JSON.stringify(payload) })
}