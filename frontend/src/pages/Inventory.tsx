import { useEffect, useState } from 'react'
import { createOpeningStock, fetchInventory, fetchInventoryFormData, transferInventory } from '../api/inventoryApi'
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

  async function loadInventory() {
    setListLoading(true)
    try { setItems((await fetchInventory()).items) }
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

  function reset() { setProductId(''); setSupplierId(''); setLocationId(''); setQuantity('') }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSuccess('')
    if (!productId || !supplierId || !locationId || !quantity || Number(quantity) <= 0) { setError('Choose a product, supplier, location, and quantity greater than zero.'); return }
    const payload: OpeningStockRequest = { product_id: Number(productId), supplier_id: Number(supplierId), quantity: Number(quantity), ...(locationType === 'store' ? { store_id: Number(locationId) } : { godown_id: Number(locationId) }) }
    setSubmitting(true)
    try { await createOpeningStock(payload); setSuccess('Opening stock added successfully.'); reset(); await loadInventory() }
    catch (submitError) { setError(submitError instanceof Error ? submitError.message : 'Unable to add opening stock.') }
    finally { setSubmitting(false) }
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

  return <div className="product-page">
    <div className="page-intro"><div><p className="eyebrow">Inventory foundation</p><h1>Inventory</h1><p className="page-description">Record opening stock and keep a clear view of every product position.</p></div><div className="page-mark">IN<span>02</span></div></div>
    {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
    {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
    {loading || !formData ? <div className="loading-panel">Preparing your inventory workspace...</div> : <>
      <form className="product-form" onSubmit={submit}>
        <div className="form-heading"><div><p className="eyebrow">Opening stock</p><h2>Add opening balance</h2></div><span className="required-note"><b>*</b> Required</span></div>
        <div className="form-grid form-grid--base inventory-form-grid">
          <label><span>Product <b>*</b></span><select value={productId} onChange={(event) => setProductId(event.target.value)}><option value="">Select product</option>{formData.products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}</select></label>
          <label><span>Supplier <b>*</b></span><select value={supplierId} onChange={(event) => setSupplierId(event.target.value)} disabled={suppliers.length === 0}><option value="">{suppliers.length ? 'Select supplier' : 'No active suppliers available'}</option>{suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select>{supplierLoadError ? <small>{supplierLoadError}</small> : suppliers.length === 0 && <small>A supplier is required. Add or activate a supplier before recording opening stock.</small>}</label>
          <label><span>Location type <b>*</b></span><select value={locationType} onChange={(event) => { setLocationType(event.target.value as 'store' | 'godown'); setLocationId('') }}><option value="store">Store</option><option value="godown">Godown</option></select></label>
          <label><span>{locationType === 'store' ? 'Store' : 'Godown'} <b>*</b></span><select value={locationId} onChange={(event) => setLocationId(event.target.value)}><option value="">Select {locationType}</option>{locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}</select></label>
          <label><span>Quantity <b>*</b></span><input type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="e.g. 5" /></label>
        </div>
        <div className="form-actions"><button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Saving...' : 'Add Opening Stock'}</button></div>
      </form>
      <form className="product-form inventory-transfer-form" onSubmit={submitTransfer}>
        <div className="form-heading"><div><p className="eyebrow">Move existing stock</p><h2>Inventory Transfer</h2></div><span className="required-note"><b>*</b> Required</span></div>
        {transferError && <div className="notice notice--error" role="alert"><strong>Transfer not completed</strong><span>{transferError}</span></div>}
        {transferSuccess && <div className="notice notice--success" role="status"><strong>Transfer complete</strong><span>{transferSuccess}</span></div>}
        <div className="form-grid form-grid--base inventory-transfer-grid">
          <label><span>Product <b>*</b></span><select value={transferProductId} onChange={(event) => { setTransferProductId(event.target.value); setSourceLocationKey(''); setDestinationLocationKey(''); setTransferQuantity(''); setTransferError(''); setTransferSuccess('') }}><option value="">Select product</option>{formData.products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}</select></label>
          <label><span>Source location <b>*</b></span><select value={sourceLocationKey} onChange={(event) => { setSourceLocationKey(event.target.value); if (event.target.value === destinationLocationKey) setDestinationLocationKey(''); setTransferQuantity(''); setTransferError('') }} disabled={!transferProductId || sourceLocations.length === 0}><option value="">{!transferProductId ? 'Select product first' : sourceLocations.length ? 'Select source' : 'No source stock available'}</option>{sourceLocations.map((location) => <option key={location.key} value={location.key}>{location.type === 'store' ? 'Store' : 'Godown'} · {location.name}</option>)}</select>{selectedSource ? <small className="transfer-availability">Available quantity: {selectedSource.availableQuantity}</small> : transferProductId && productBalances.length === 0 ? <small>Select a product with an inventory balance to transfer.</small> : hasAmbiguousSourceLocation && <small>Some source balances could not be matched to a unique location.</small>}</label>
          <label><span>Destination location <b>*</b></span><select value={destinationLocationKey} onChange={(event) => { setDestinationLocationKey(event.target.value); setTransferError('') }} disabled={!selectedSource}><option value="">{selectedSource ? 'Select destination' : 'Select source first'}</option>{destinationLocations.map((location) => <option key={location.key} value={location.key} disabled={location.key === sourceLocationKey}>{location.type === 'store' ? 'Store' : 'Godown'} · {location.name}{location.key === sourceLocationKey ? ' (source)' : ''}</option>)}</select></label>
          <label className={transferQuantityError ? 'has-error' : ''}><span>Quantity <b>*</b></span><input type="number" min="1" step="1" value={transferQuantity} onChange={(event) => { setTransferQuantity(event.target.value); setTransferError('') }} placeholder="e.g. 5" aria-invalid={Boolean(transferQuantityError)} aria-describedby={transferQuantityError ? 'transfer-quantity-error' : undefined} />{transferQuantityError && <small id="transfer-quantity-error">{transferQuantityError}</small>}</label>
        </div>
        <div className="form-actions">
          <button type="button" className="secondary-button" onClick={resetTransfer} disabled={transferSubmitting}>Reset</button>
          <button type="submit" className="primary-button" disabled={!transferCanSubmit}>{transferSubmitting ? 'Transferring...' : 'Transfer Stock'}</button>
        </div>
      </form>
      <section className="product-list-panel inventory-list"><div className="section-heading section-heading--list"><div><p className="eyebrow">Current position</p><h2>Inventory list</h2></div><span>{items.length} records</span></div>
        {listLoading ? <div className="table-loading">Loading inventory...</div> : items.length === 0 ? <div className="empty-state">No inventory balances yet.</div> : <div className="table-wrap"><table><thead><tr><th>Product</th><th>SKU</th><th>Location</th><th>Quantity</th><th>Reserved</th><th>Available</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td className="product-name-cell">{item.product_name}</td><td className="mono">{item.sku}</td><td>{item.location.name} <small>({item.location.type})</small></td><td>{item.quantity}</td><td>{item.reserved_quantity}</td><td className="available-value">{item.available_quantity}</td></tr>)}</tbody></table></div>}
      </section>
    </>}
  </div>
}