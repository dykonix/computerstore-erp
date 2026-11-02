import { Fragment, useEffect, useMemo, useState } from 'react'
import { createOpeningStock, fetchInventory, fetchInventoryFormData, transferInventory, updateInventoryCostPrice } from '../api/inventoryApi'
import type { InventoryFormData, InventoryItem, InventoryTransferRequest, OpeningStockRequest } from '../api/inventoryApi'
import { fetchSuppliers } from '../api/supplierApi'
import type { Supplier } from '../api/supplierApi'

type TransferLocation = {
  key: string
  type: 'store' | 'godown'
  id: number
  name: string
}

type SourceLocation = TransferLocation & { availableQuantity: number }

function getTransferErrorMessage(error: unknown): string {
  if (!(error instanceof Error)) return 'Transfer could not be completed. Please try again.'
  const message = error.message
  const normalized = message.toLowerCase()
  if (normalized.includes('transfer quantity exceeds available stock')) {
    return 'Available stock changed before the transfer completed. Refresh the balances and try again.'
  }
  if (normalized.includes('source inventory balance does not exist')) {
    return 'The selected source no longer has an inventory balance. Refresh the balances and try again.'
  }
  if (normalized.includes('source and destination locations must be different')) {
    return 'Choose different source and destination locations.'
  }
  if (normalized.includes('source location')) return 'The selected source location is no longer available.'
  if (normalized.includes('destination location')) return 'The selected destination location is no longer available.'
  if (normalized.includes('product does not exist or is inactive')) return 'The selected product is no longer active.'
  if (message === 'Failed to fetch' || message.startsWith('Request failed with status')) {
    return 'Unable to complete the transfer right now. Check your connection and try again.'
  }
  return message
}

export default function Inventory() {
  const [formData, setFormData] = useState<InventoryFormData | null>(null)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<InventoryItem[]>([])
  const [locationType, setLocationType] = useState<'store' | 'godown'>('store')
  const [productId, setProductId] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [locationId, setLocationId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const [editingInventoryId, setEditingInventoryId] = useState<number | null>(null)
  const [editingCostPrice, setEditingCostPrice] = useState('')
  const [costPriceSubmitting, setCostPriceSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [listLoading, setListLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [supplierLoadError, setSupplierLoadError] = useState('')
  const [transferProductId, setTransferProductId] = useState('')
  const [sourceLocationKey, setSourceLocationKey] = useState('')
  const [destinationLocationKey, setDestinationLocationKey] = useState('')
  const [transferQuantity, setTransferQuantity] = useState('')
  const [transferSubmitting, setTransferSubmitting] = useState(false)
  const [transferError, setTransferError] = useState('')
  const [transferSuccess, setTransferSuccess] = useState('')
  const [activeForm, setActiveForm] = useState<'opening' | 'transfer' | null>(null)
  const [search, setSearch] = useState('')
  const [selectedLocation, setSelectedLocation] = useState('all')
  const [expandedProducts, setExpandedProducts] = useState<number[]>([])
  const [showAllProducts, setShowAllProducts] = useState(false)

  async function loadInventory() {
    setListLoading(true)
    try {
      const nextItems = (await fetchInventory()).items
      setItems(nextItems)
      setExpandedProducts((current) => {
        if (current.length) return current.filter((id) => nextItems.some((item) => item.product_id === id))
        const firstProductId = nextItems[0]?.product_id
        return firstProductId === undefined ? [] : [firstProductId]
      })
    }
    catch (loadError) { setError(loadError instanceof Error ? loadError.message : 'Unable to load inventory.') }
    finally { setListLoading(false) }
  }

  useEffect(() => {
    async function load() {
      try {
        const [data] = await Promise.all([fetchInventoryFormData(), loadInventory()])
        setFormData(data)
      } catch (loadError) { setError(loadError instanceof Error ? loadError.message : 'Unable to load inventory form data.') }
      try {
        const supplierResponse = await fetchSuppliers(1, 100, true)
        setSuppliers(supplierResponse.items.filter((supplier) => supplier.is_active))
        setSupplierLoadError('')
      } catch (supplierError) {
        const message = supplierError instanceof Error ? supplierError.message : 'Request failed.'
        setSupplierLoadError(`Unable to load active suppliers: ${message}`)
        setError(`Unable to load active suppliers: ${message}`)
      } finally { setLoading(false) }
    }
    void load()
  }, [])

  function reset() { setProductId(''); setSupplierId(''); setLocationId(''); setQuantity(''); setCostPrice('') }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSuccess('')
    if (!productId || !supplierId || !locationId || !quantity || Number(quantity) <= 0) { setError('Choose a product, supplier, location, and quantity greater than zero.'); return }
    if (costPrice === '' || !Number.isFinite(Number(costPrice)) || Number(costPrice) < 0) { setError('Enter a cost price of zero or more.'); return }
    const payload: OpeningStockRequest = { product_id: Number(productId), supplier_id: Number(supplierId), quantity: Number(quantity), cost_price: Number(costPrice), ...(locationType === 'store' ? { store_id: Number(locationId) } : { godown_id: Number(locationId) }) }
    setSubmitting(true)
    try { await createOpeningStock(payload); setSuccess('Opening stock added successfully.'); reset(); await loadInventory() }
    catch (submitError) { setError(submitError instanceof Error ? submitError.message : 'Unable to add opening stock.') }
    finally { setSubmitting(false) }
  }

  async function saveCostPrice(item: InventoryItem) {
    const nextCostPrice = Number(editingCostPrice)
    if (editingCostPrice === '' || !Number.isFinite(nextCostPrice) || nextCostPrice < 0) {
      setError('Enter a cost price of zero or more.')
      return
    }
    setCostPriceSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await updateInventoryCostPrice(item.id, nextCostPrice)
      setEditingInventoryId(null)
      setEditingCostPrice('')
      setSuccess('Inventory cost price updated successfully.')
      await loadInventory()
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : 'Unable to update inventory cost price.')
    } finally {
      setCostPriceSubmitting(false)
    }
  }

  const locations = locationType === 'store' ? formData?.stores ?? [] : formData?.godowns ?? []
  const destinationLocations: TransferLocation[] = [
    ...(formData?.stores.map((store) => ({ key: `store:${store.id}`, type: 'store' as const, ...store })) ?? []),
    ...(formData?.godowns.map((godown) => ({ key: `godown:${godown.id}`, type: 'godown' as const, ...godown })) ?? []),
  ]
  const productBalances = transferProductId
    ? items.filter((item) => item.product_id === Number(transferProductId))
    : []
  const sourceLocationMatches = productBalances.map((balance) => {
    const isStore = balance.location.type.toLowerCase() === 'store'
    const type: TransferLocation['type'] = isStore ? 'store' : 'godown'
    const candidates = isStore ? formData?.stores ?? [] : formData?.godowns ?? []
    const matches = candidates.filter((location) => location.name === balance.location.name)
    return { balance, type, matches }
  })
  const hasAmbiguousSourceLocation = sourceLocationMatches.some(({ matches }) => matches.length > 1)
  const sourceLocations: SourceLocation[] = sourceLocationMatches.flatMap(({ balance, type, matches }) => {
    if (matches.length !== 1) return []
    const location = matches[0]
    return [{ key: `${type}:${location.id}`, type, id: location.id, name: location.name, availableQuantity: balance.available_quantity }]
  })
  const selectedSource = sourceLocations.find((location) => location.key === sourceLocationKey)
  const selectedDestination = destinationLocations.find((location) => location.key === destinationLocationKey)
  const quantityValue = Number(transferQuantity)
  const transferQuantityError = transferQuantity === ''
    ? ''
    : !Number.isInteger(quantityValue) || quantityValue <= 0
      ? 'Enter a positive whole number.'
      : selectedSource && quantityValue > selectedSource.availableQuantity
        ? `Transfer quantity cannot exceed available quantity (${selectedSource.availableQuantity}).`
        : ''
  const transferCanSubmit = Boolean(
    transferProductId && selectedSource && selectedDestination && transferQuantity &&
    !transferQuantityError && sourceLocationKey !== destinationLocationKey && !transferSubmitting,
  )

  function resetTransfer() {
    setTransferProductId('')
    setSourceLocationKey('')
    setDestinationLocationKey('')
    setTransferQuantity('')
    setTransferError('')
    setTransferSuccess('')
  }

  async function submitTransfer(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setTransferError('')
    setTransferSuccess('')
    if (!transferCanSubmit || !selectedSource || !selectedDestination) return

    const payload: InventoryTransferRequest = {
      product_id: Number(transferProductId),
      source_store_id: selectedSource.type === 'store' ? selectedSource.id : null,
      source_godown_id: selectedSource.type === 'godown' ? selectedSource.id : null,
      destination_store_id: selectedDestination.type === 'store' ? selectedDestination.id : null,
      destination_godown_id: selectedDestination.type === 'godown' ? selectedDestination.id : null,
      quantity: quantityValue,
    }

    setTransferSubmitting(true)
    try {
      const result = await transferInventory(payload)
      setTransferSuccess(`Transferred ${quantityValue} ${quantityValue === 1 ? 'unit' : 'units'} to ${result.location.name} (${result.location.type}).`)
      setTransferProductId('')
      setSourceLocationKey('')
      setDestinationLocationKey('')
      setTransferQuantity('')
      await loadInventory()
    } catch (submitError) {
      setTransferError(getTransferErrorMessage(submitError))
    } finally {
      setTransferSubmitting(false)
    }
  }

  const locationOptions = useMemo(() => {
    const options = new Map<string, string>()
    items.forEach((item) => options.set(`${item.location.type}:${item.location.name}`, `${item.location.name} (${item.location.type})`))
    return Array.from(options.entries()).sort((a, b) => a[1].localeCompare(b[1]))
  }, [items])

  const filteredItems = useMemo(() => items.filter((item) => {
    const query = search.trim().toLowerCase()
    const matchesSearch = !query || [item.product_name, item.sku, item.brand, item.category].some((value) => value?.toLowerCase().includes(query))
    const matchesLocation = selectedLocation === 'all' || `${item.location.type}:${item.location.name}` === selectedLocation
    return matchesSearch && matchesLocation
  }), [items, search, selectedLocation])

  const groupedProducts = useMemo(() => {
    const groups = new Map<number, { productId: number; name: string; sku: string; brand: string; category: string; balances: InventoryItem[]; quantity: number; reserved: number; available: number; costTotal: number; costUnits: number }>()
    filteredItems.forEach((item) => {
      let group = groups.get(item.product_id)
      if (!group) {
        group = { productId: item.product_id, name: item.product_name, sku: item.sku, brand: item.brand, category: item.category, balances: [], quantity: 0, reserved: 0, available: 0, costTotal: 0, costUnits: 0 }
        groups.set(item.product_id, group)
      }
      group.balances.push(item)
      group.quantity += Number(item.quantity) || 0
      group.reserved += Number(item.reserved_quantity) || 0
      group.available += Number(item.available_quantity) || 0
      const cost = Number(item.cost_price)
      if (Number.isFinite(cost) && cost >= 0) { group.costTotal += cost * (Number(item.quantity) || 0); group.costUnits += Number(item.quantity) || 0 }
    })
    return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name))
  }, [filteredItems])

  const categorySummary = useMemo(() => {
    const totals = new Map<string, number>()
    filteredItems.forEach((item) => totals.set(item.category || 'Uncategorised', (totals.get(item.category || 'Uncategorised') || 0) + (Number(item.quantity) || 0)))
    return Array.from(totals.entries()).sort((a, b) => b[1] - a[1])
  }, [filteredItems])

  const visibleProducts = showAllProducts ? groupedProducts : groupedProducts.slice(0, 5)

  function toggleProduct(productId: number) {
    setExpandedProducts((current) => current.includes(productId) ? current.filter((id) => id !== productId) : [...current, productId])
  }

  return <div className="product-page inventory-redesign">
    <style>{`
      .inventory-redesign .inventory-header{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:22px}
      .inventory-redesign .inventory-header h1{font-size:clamp(2.2rem,5vw,3.4rem);line-height:1.02}
      .inventory-redesign .inventory-header-actions{display:flex;gap:10px;flex-wrap:wrap}
      .inventory-redesign .inventory-action{display:inline-flex;align-items:center;justify-content:center;gap:10px;border:0;border-radius:4px;padding:14px 20px;background:var(--red);color:#fff;font:inherit;font-weight:800;cursor:pointer}
      .inventory-redesign .inventory-action:hover{background:var(--red-dark)}
      .inventory-redesign .inventory-toolbar{display:grid;grid-template-columns:minmax(220px,1fr) minmax(230px,340px);gap:22px;align-items:center;border:1px solid var(--line);border-radius:4px;padding:16px 20px;background:var(--panel);margin-bottom:16px}
      .inventory-redesign .inventory-search{display:flex;align-items:center;gap:12px;border:1px solid #cfc6bc;border-radius:4px;padding:0 14px;background:#fff}
      .inventory-redesign .inventory-search input{width:100%;min-width:0;border:0;outline:0;padding:12px 0;background:transparent;font:inherit}
      .inventory-redesign .inventory-location-filter{display:flex;align-items:center;gap:12px}
      .inventory-redesign .inventory-location-filter label{white-space:nowrap}
      .inventory-redesign .inventory-location-filter select{min-width:0;width:100%;border:1px solid #cfc6bc;border-radius:4px;padding:12px;background:#fff;font:inherit}
      .inventory-redesign .inventory-category-cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:16px 0 20px}
      .inventory-redesign .inventory-category-card{display:flex;align-items:center;gap:14px;min-width:0;border:1px solid var(--line);border-radius:5px;padding:16px;background:var(--panel)}
      .inventory-redesign .inventory-category-icon{display:grid;place-items:center;flex:0 0 52px;width:52px;height:52px;border-radius:50%;background:#f6e8e6;color:var(--red);font-size:1.25rem;font-weight:800}
      .inventory-redesign .inventory-category-card:nth-child(5n+2) .inventory-category-icon{background:#e8f0f8;color:#2769a8}.inventory-redesign .inventory-category-card:nth-child(5n+3) .inventory-category-icon{background:#e8f2e9;color:#28754c}.inventory-redesign .inventory-category-card:nth-child(5n+4) .inventory-category-icon{background:#fbefe0;color:#bd6b19}.inventory-redesign .inventory-category-card:nth-child(5n+5) .inventory-category-icon{background:#eee8f6;color:#7452a8}
      .inventory-redesign .inventory-category-card p{margin:0 0 3px;font-size:.82rem;font-weight:700}.inventory-redesign .inventory-category-card strong{display:block;font:700 1.8rem Georgia,serif;color:var(--ink)}.inventory-redesign .inventory-category-card small{color:var(--muted)}
      .inventory-redesign .inventory-table-wrap{overflow:auto}.inventory-redesign .inventory-table{width:100%;border-collapse:collapse;min-width:760px}.inventory-redesign .inventory-table th{padding:15px 18px;border-bottom:1px solid var(--line);color:#625d57;font-size:.7rem;letter-spacing:.09em;text-align:left;text-transform:uppercase;white-space:nowrap}.inventory-redesign .inventory-table td{padding:11px 18px;border-bottom:1px solid #eee8e1;vertical-align:middle}.inventory-redesign .inventory-table .numeric{text-align:center;font-weight:700;font-variant-numeric:tabular-nums}.inventory-redesign .inventory-table .reserved-value{color:#c76512}.inventory-redesign .inventory-table .available-value{color:var(--green)}
      .inventory-redesign .inventory-product-row{cursor:pointer}.inventory-redesign .inventory-product-row:hover{background:#fcf8f3}.inventory-redesign .inventory-product-name{display:flex;align-items:center;gap:14px;min-width:250px}.inventory-redesign .inventory-product-thumb{display:grid;place-items:center;flex:0 0 54px;width:54px;height:50px;border-radius:4px;background:#f5f1eb;color:#716b64;font-size:1.4rem}.inventory-redesign .inventory-product-name strong{display:block;color:var(--ink);font-size:.88rem}.inventory-redesign .inventory-product-name small{display:block;margin-top:4px;color:var(--muted);font-size:.75rem}.inventory-redesign .inventory-chevron{width:22px;display:inline-block;font-size:1.1rem}.inventory-redesign .inventory-location-row td{padding:0 18px 12px}.inventory-redesign .inventory-location-table{width:100%;border:1px solid var(--line);border-collapse:separate;border-spacing:0;border-radius:4px;overflow:hidden}.inventory-redesign .inventory-location-table th,.inventory-redesign .inventory-location-table td{padding:11px 14px;border-bottom:1px solid #eee8e1}.inventory-redesign .inventory-location-table th{background:#faf7f2}.inventory-redesign .inventory-location-table tr:last-child td{border-bottom:0}.inventory-redesign .inventory-location-table th:not(:first-child),.inventory-redesign .inventory-location-table td:not(:first-child){text-align:center}.inventory-redesign .inventory-cost-edit{justify-content:center}.inventory-redesign .inventory-bottom{padding:14px 18px;display:flex;justify-content:center}.inventory-redesign .inventory-show-more{border:1px solid var(--line);border-radius:3px;padding:9px 14px;background:#fff;color:var(--red);font:inherit;font-weight:700;cursor:pointer}
      .inventory-redesign .inventory-form-panel{margin:0 0 18px}.inventory-redesign .inventory-form-panel .product-form{box-shadow:none}.inventory-redesign .inventory-form-close{border:1px solid var(--line);background:#fff;color:var(--muted);padding:7px 11px;cursor:pointer}
      @media(max-width:1000px){.inventory-redesign .inventory-category-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.inventory-redesign .inventory-toolbar{grid-template-columns:1fr}}
      @media(max-width:640px){.inventory-redesign .inventory-header{align-items:flex-start;flex-direction:column}.inventory-redesign .inventory-category-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.inventory-redesign .inventory-category-card{padding:12px;gap:9px}.inventory-redesign .inventory-category-icon{flex-basis:40px;width:40px;height:40px}.inventory-redesign .inventory-category-card strong{font-size:1.4rem}.inventory-redesign .inventory-location-filter{align-items:flex-start;flex-direction:column;gap:6px}}
    `}</style>
    <div className="inventory-header">
      <div><p className="eyebrow">Inventory foundation</p><h1>Inventory</h1><p className="page-description">Track stock across stores and godowns.</p></div>
      <div className="inventory-header-actions">
        <button type="button" className="inventory-action" onClick={() => { setActiveForm(activeForm === 'opening' ? null : 'opening'); setError(''); setSuccess('') }}><span aria-hidden="true">＋</span> Add Inventory</button>
        <button type="button" className="inventory-action" onClick={() => { setActiveForm(activeForm === 'transfer' ? null : 'transfer'); setTransferError(''); setTransferSuccess('') }}><span aria-hidden="true">⇄</span> Move Inventory</button>
      </div>
    </div>
    {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
    {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
    {loading || !formData ? <div className="loading-panel">Preparing your inventory workspace...</div> : <>
      {activeForm === 'opening' && <div className="inventory-form-panel"><form className="product-form" onSubmit={submit}>
        <div className="form-heading"><div><p className="eyebrow">Opening stock</p><h2>Add inventory</h2></div><button type="button" className="inventory-form-close" onClick={() => setActiveForm(null)}>Close</button></div>
        <div className="form-grid form-grid--base inventory-form-grid">
          <label><span>Product <b>*</b></span><select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Select product</option>{formData.products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}</select></label>
          <label><span>Supplier <b>*</b></span><select value={supplierId} onChange={(event) => setSupplierId(event.target.value)} disabled={suppliers.length === 0}><option value="">{suppliers.length ? 'Select supplier' : 'No active suppliers available'}</option>{suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select>{supplierLoadError ? <small>{supplierLoadError}</small> : suppliers.length === 0 && <small>A supplier is required. Add or activate a supplier before recording opening stock.</small>}</label>
          <label><span>Location type <b>*</b></span><select value={locationType} onChange={(event) => { setLocationType(event.target.value as 'store' | 'godown'); setLocationId('') }}><option value="store">Store</option><option value="godown">Godown</option></select></label>
          <label><span>{locationType === 'store' ? 'Store' : 'Godown'} <b>*</b></span><select value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="">Select {locationType}</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label>
          <label><span>Quantity <b>*</b></span><input type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="e.g. 5" /></label>
          <label><span>Cost Price <b>*</b></span><input type="number" min="0" step="0.01" value={costPrice} onChange={(event) => setCostPrice(event.target.value)} placeholder="e.g. 450.00" /></label>
        </div>
        <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setActiveForm(null)}>Cancel</button><button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Saving...' : 'Add Opening Stock'}</button></div>
      </form></div>}
      {activeForm === 'transfer' && <div className="inventory-form-panel"><form className="product-form inventory-transfer-form" onSubmit={submitTransfer}>
        <div className="form-heading"><div><p className="eyebrow">Move existing stock</p><h2>Inventory transfer</h2></div><button type="button" className="inventory-form-close" onClick={() => setActiveForm(null)}>Close</button></div>
        {transferError && <div className="notice notice--error" role="alert"><strong>Transfer not completed</strong><span>{transferError}</span></div>}{transferSuccess && <div className="notice notice--success" role="status"><strong>Transfer complete</strong><span>{transferSuccess}</span></div>}
        <div className="form-grid form-grid--base inventory-transfer-grid">
          <label><span>Product <b>*</b></span><select value={transferProductId} onChange={(event) => { setTransferProductId(event.target.value); setSourceLocationKey(''); setDestinationLocationKey(''); setTransferQuantity(''); setTransferError(''); setTransferSuccess('') }}><option value="">Select product</option>{formData.products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}</select></label>
          <label><span>Source location <b>*</b></span><select value={sourceLocationKey} onChange={(event) => { setSourceLocationKey(event.target.value); if (event.target.value === destinationLocationKey) setDestinationLocationKey(''); setTransferQuantity(''); setTransferError('') }} disabled={!transferProductId || sourceLocations.length === 0}><option value="">{!transferProductId ? 'Select product first' : sourceLocations.length ? 'Select source' : 'No source stock available'}</option>{sourceLocations.map((location) => <option key={location.key} value={location.key}>{location.type === 'store' ? 'Store' : 'Godown'} · {location.name}</option>)}</select>{selectedSource ? <small className="transfer-availability">Available quantity: {selectedSource.availableQuantity}</small> : transferProductId && productBalances.length === 0 ? <small>Select a product with an inventory balance to transfer.</small> : hasAmbiguousSourceLocation && <small>Some source balances could not be matched to a unique location.</small>}</label>
          <label><span>Destination location <b>*</b></span><select value={destinationLocationKey} onChange={(event) => { setDestinationLocationKey(event.target.value); setTransferError('') }} disabled={!selectedSource}><option value="">{selectedSource ? 'Select destination' : 'Select source first'}</option>{destinationLocations.map((location) => <option key={location.key} value={location.key} disabled={location.key === sourceLocationKey}>{location.type === 'store' ? 'Store' : 'Godown'} · {location.name}{location.key === sourceLocationKey ? ' (source)' : ''}</option>)}</select></label>
          <label className={transferQuantityError ? 'has-error' : ''}><span>Quantity <b>*</b></span><input type="number" min="1" step="1" value={transferQuantity} onChange={(event) => { setTransferQuantity(event.target.value); setTransferError('') }} placeholder="e.g. 5" aria-invalid={Boolean(transferQuantityError)} aria-describedby={transferQuantityError ? 'transfer-quantity-error' : undefined} />{transferQuantityError && <small id="transfer-quantity-error">{transferQuantityError}</small>}</label>
        </div>
        <div className="form-actions"><button type="button" className="secondary-button" onClick={resetTransfer} disabled={transferSubmitting}>Reset</button><button type="button" className="secondary-button" onClick={() => setActiveForm(null)} disabled={transferSubmitting}>Cancel</button><button type="submit" className="primary-button" disabled={!transferCanSubmit}>{transferSubmitting ? 'Transferring...' : 'Transfer Stock'}</button></div>
      </form></div>}
      <div className="inventory-toolbar">
        <div className="inventory-search"><span aria-hidden="true">⌕</span><input aria-label="Search inventory" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search product, SKU or model" /></div>
        <div className="inventory-location-filter"><label htmlFor="inventory-location">Location</label><select id="inventory-location" value={selectedLocation} onChange={(event) => setSelectedLocation(event.target.value)}><option value="all">All Locations</option>{locationOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      </div>
      <div className="inventory-category-cards">{categorySummary.slice(0, 5).map(([category, total], index) => <div className="inventory-category-card" key={category}><div className="inventory-category-icon" aria-hidden="true">{['▱', '▣', '▤', '▯', '▧'][index]}</div><div><p>{category}</p><strong>{total}</strong><small>Total units</small></div></div>)}</div>
      <section className="product-list-panel inventory-list">
        {listLoading ? <div className="table-loading" style={{ padding: 24 }}>Loading inventory...</div> : groupedProducts.length === 0 ? <div className="empty-state" style={{ padding: 24 }}>No inventory balances match your search.</div> : <>
          <div className="inventory-table-wrap"><table className="inventory-table"><thead><tr><th aria-label="Expand product"></th><th>Product</th><th className="numeric">On-hand ↕</th><th className="numeric">Reserved ↕</th><th className="numeric">Available ↕</th><th className="numeric">Cost price ↕</th></tr></thead><tbody>
            {visibleProducts.map((product) => <Fragment key={product.productId}>
              <tr className="inventory-product-row" key={`product-${product.productId}`} onClick={() => toggleProduct(product.productId)} aria-expanded={expandedProducts.includes(product.productId)}>
                <td><span className="inventory-chevron">{expandedProducts.includes(product.productId) ? '⌄' : '›'}</span></td>
                <td><div className="inventory-product-name"><span className="inventory-product-thumb" aria-hidden="true">{product.category?.toLowerCase().includes('printer') ? '▤' : product.category?.toLowerCase().includes('desktop') ? '▣' : '▱'}</span><span><strong>{product.name}</strong><small>SKU: {product.sku}</small></span></div></td>
                <td className="numeric">{product.quantity}</td><td className="numeric reserved-value">{product.reserved}</td><td className="numeric available-value">{product.available}</td><td className="numeric">{product.costUnits > 0 ? (product.costTotal / product.costUnits).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</td>
              </tr>
              {expandedProducts.includes(product.productId) && <tr className="inventory-location-row" key={`locations-${product.productId}`}><td colSpan={6}><table className="inventory-location-table"><thead><tr><th>Location</th><th>Type</th><th>On-hand</th><th>Reserved</th><th>Available</th><th>Cost price</th></tr></thead><tbody>{product.balances.map((item) => <tr key={item.id}><td>{item.location.name}</td><td>{item.location.type}</td><td>{item.quantity}</td><td className="reserved-value">{item.reserved_quantity}</td><td className="available-value">{item.available_quantity}</td><td>{editingInventoryId === item.id ? <div className="inventory-cost-edit"><input aria-label={`Cost price for ${item.product_name}`} type="number" min="0" step="0.01" value={editingCostPrice} onChange={(event) => setEditingCostPrice(event.target.value)} /><button type="button" className="row-action" onClick={(event) => { event.stopPropagation(); void saveCostPrice(item) }} disabled={costPriceSubmitting}>Save</button><button type="button" className="row-action" onClick={(event) => { event.stopPropagation(); setEditingInventoryId(null); setEditingCostPrice('') }} disabled={costPriceSubmitting}>Cancel</button></div> : <>{Number(item.cost_price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} <button type="button" className="row-action" onClick={(event) => { event.stopPropagation(); setEditingInventoryId(item.id); setEditingCostPrice(String(item.cost_price)) }}>Edit</button></>}</td></tr>)}</tbody></table></td></tr>}
            </Fragment>)}
          </tbody></table></div>
          {groupedProducts.length > 5 && <div className="inventory-bottom"><button type="button" className="inventory-show-more" onClick={() => setShowAllProducts((current) => !current)}>{showAllProducts ? 'Show fewer products' : `Show all ${groupedProducts.length} products`}</button></div>}
        </>}
      </section>
    </>}
  </div>
}
