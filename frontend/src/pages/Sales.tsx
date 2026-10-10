import { useEffect, useMemo, useState } from 'react'
import {
  addSaleItem,
  addSalePayment,
  confirmSale,
  createSale,
  deliverSale,
  fetchSale,
  fetchSalePayments,
  reserveSale,
} from '../api/salesApi'
import type {
  SalePaymentResponse,
  SaleItemResponse,
  SaleResponse,
} from '../api/salesApi'
import {
  fetchCurrentProductPrice,
  fetchProducts,
} from '../api/productApi'
import type {
  ProductListItem,
  ProductPriceResponse,
} from '../api/productApi'
import { fetchAllowedStores } from '../api/storesApi'
import type { Store } from '../api/storesApi'
import {
  createCustomer,
  searchCustomers,
} from '../api/customerApi'
import type { Customer } from '../api/customerApi'
import { fetchInventory } from '../api/inventoryApi'
import type { InventoryItem } from '../api/inventoryApi'
import {
  fetchProductPromotions,
} from '../api/promotionApi'
import type { ProductPromotion } from '../api/promotionApi'

export default function Sales() {
  const [stores, setStores] = useState<Store[]>([])
  const [products, setProducts] = useState<ProductListItem[]>([])

  const [storeId, setStoreId] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState(1)

  const [customerSelectionMode, setCustomerSelectionMode] = useState<
    'walkin' | 'existing' | 'new'
  >('walkin')
  const [customerQuery, setCustomerQuery] = useState('')
  const [customerSearchResults, setCustomerSearchResults] = useState<
    Customer[]
  >([])
  const [newCustomerForm, setNewCustomerForm] = useState({
    name: '',
    mobile: '',
    email: '',
    address: '',
  })
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(
    null,
  )

  const [sale, setSale] = useState<SaleResponse | null>(null)
  const [items, setItems] = useState<SaleItemResponse[]>([])
  const [payments, setPayments] = useState<SalePaymentResponse[]>([])
  const [paymentMode, setPaymentMode] = useState('CASH')
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentReference, setPaymentReference] = useState('')

  const [selectedProductPrice, setSelectedProductPrice] = useState<
    ProductPriceResponse | null
  >(null)
  const [selectedProductInventory, setSelectedProductInventory] =
    useState<InventoryItem | null>(null)
  const [availablePromotions, setAvailablePromotions] = useState<
    ProductPromotion[]
  >([])
  const [selectedPromotionId, setSelectedPromotionId] = useState<
    number | null
  >(null)
  const [actualPriceInput, setActualPriceInput] = useState('')
  const [minimumPriceOverride, setMinimumPriceOverride] = useState(false)
  const [isFreeProduct, setIsFreeProduct] = useState(false)

  const [loading, setLoading] = useState(true)
  const [addingItem, setAddingItem] = useState(false)
  const [reserving, setReserving] = useState(false)
  const [savingPayment, setSavingPayment] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [delivering, setDelivering] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const selectedStore = stores.find(
    (store) => String(store.id) === storeId,
  )

  const selectedProduct = products.find(
    (product) => product.id === Number(productId),
  )

  const productMap = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  )

  const configuredPrice = selectedProductPrice?.sale_price ?? 0
  const minimumPrice = selectedProductPrice?.minimum_sale_price ?? null
  const actualSalePrice = isFreeProduct
    ? 0
    : Number(actualPriceInput || configuredPrice || 0)
  const belowMinimumPrice =
    !isFreeProduct &&
    minimumPrice !== null &&
    actualSalePrice < minimumPrice &&
    !minimumPriceOverride
  const isSaleEditable = sale === null || sale.status === 'DRAFT'
  const paidAmount = payments.reduce(
    (total, payment) => total + Number(payment.amount),
    0,
  )
  const remainingPayable = Math.max(
    0,
    Number(sale?.payable_amount ?? 0) - paidAmount,
  )
  const isFullyPaid =
    sale !== null &&
    Math.round(paidAmount * 100) ===
      Math.round(Number(sale.payable_amount) * 100)

  useEffect(() => {
    async function loadSalesData() {
      setLoading(true)
      setError('')

      try {
        const [storeResponse, productResponse] =
          await Promise.all([
            fetchAllowedStores(),
            fetchProducts(),
          ])

        setStores(storeResponse)
        setProducts(
          productResponse.items.filter((product) => product.is_active),
        )
        if (storeResponse.length === 1) {
          setStoreId(String(storeResponse[0].id))
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load sales data.',
        )
      } finally {
        setLoading(false)
      }
    }

    void loadSalesData()
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadProductContext() {
      if (!selectedProduct || !storeId) {
        setSelectedProductPrice(null)
        setSelectedProductInventory(null)
        setAvailablePromotions([])
        setSelectedPromotionId(null)
        setActualPriceInput('')
        setMinimumPriceOverride(false)
        setIsFreeProduct(false)
        return
      }

      try {
        const [priceResponse, inventoryResponse, promotionResponse] =
          await Promise.all([
            fetchCurrentProductPrice(selectedProduct.id),
            fetchInventory(selectedProduct.id, Number(storeId)),
            fetchProductPromotions(selectedProduct.id),
          ])

        if (cancelled) {
          return
        }

        const matchingInventory = inventoryResponse.items[0] ?? null

        setSelectedProductPrice(priceResponse)
        setSelectedProductInventory(matchingInventory)
        setAvailablePromotions(promotionResponse)
        setSelectedPromotionId(null)
        setActualPriceInput(
          priceResponse ? String(priceResponse.sale_price) : '0',
        )
        setMinimumPriceOverride(false)
        setIsFreeProduct(false)
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Unable to load product details.',
          )
        }
      }
    }

    void loadProductContext()

    return () => {
      cancelled = true
    }
  }, [selectedProduct, selectedStore, storeId])

  async function handleCustomerSearch() {
    const query = customerQuery.trim()

    if (!query) {
      setCustomerSearchResults([])
      return
    }

    try {
      const results = await searchCustomers(query)
      setCustomerSearchResults(results)
    } catch (searchError) {
      setError(
        searchError instanceof Error
          ? searchError.message
          : 'Unable to search customers.',
      )
    }
  }

  async function handleCreateCustomer() {
    const name = newCustomerForm.name.trim()
    const mobile = newCustomerForm.mobile.trim()

    if (!name || !mobile) {
      setError('Customer name and mobile number are required.')
      return
    }

    try {
      const createdCustomer = await createCustomer({
        name,
        mobile,
        email: newCustomerForm.email.trim() || null,
        address: newCustomerForm.address.trim() || null,
      })

      setCustomerId(String(createdCustomer.id))
      setSelectedCustomer(createdCustomer)
      setCustomerSelectionMode('existing')
      setCustomerQuery(createdCustomer.name)
      setCustomerSearchResults([])
      setNewCustomerForm({ name: '', mobile: '', email: '', address: '' })
      setSuccess('New customer created and linked to this sale.')
      setError('')
    } catch (createError) {
      setError(
        createError instanceof Error
          ? createError.message
          : 'Unable to create the customer.',
      )
    }
  }

  function resetSale() {
    setSale(null)
    setItems([])
    setPayments([])
    setPaymentMode('CASH')
    setPaymentAmount('')
    setPaymentReference('')
    setCustomerId('')
    setCustomerQuery('')
    setCustomerSearchResults([])
    setSelectedCustomer(null)
    setCustomerSelectionMode('walkin')
    setNewCustomerForm({ name: '', mobile: '', email: '', address: '' })
    setProductId('')
    setQuantity(1)
    setSelectedPromotionId(null)
    setActualPriceInput('')
    setMinimumPriceOverride(false)
    setIsFreeProduct(false)
    setSuccess('')
    setError('')
  }

  async function handleAddProduct() {
    if (!storeId) {
      setError('Please select a store.')
      return
    }

    if (!selectedProduct) {
      setError('Please select a product.')
      return
    }

    if (customerSelectionMode !== 'walkin' && !customerId) {
      setError('Select an existing customer or create the new customer first.')
      return
    }

    if (quantity <= 0) {
      setError('Quantity must be greater than zero.')
      return
    }

    if (
      !isFreeProduct &&
      minimumPrice !== null &&
      actualSalePrice < minimumPrice &&
      !minimumPriceOverride
    ) {
      setError(
        'Price is below the configured minimum selling price. Please confirm the override before adding the item.',
      )
      return
    }

    const availableQuantity =
      selectedProductInventory?.available_quantity ?? 0
    if (quantity > availableQuantity) {
      setError(
        `Available quantity at ${selectedStore?.name ?? 'the selected store'} is ${availableQuantity}. Please reduce the requested quantity.`,
      )
      return
    }

    setAddingItem(true)
    setError('')
    setSuccess('')

    try {
      let currentSale = sale

      if (!currentSale) {
        currentSale = await createSale({
          store_id: Number(storeId),
          customer_id: customerId ? Number(customerId) : null,
        })

        setSale(currentSale)
      }

      await addSaleItem(currentSale.id, {
        product_id: selectedProduct.id,
        quantity,
        actual_unit_price: isFreeProduct ? 0 : actualSalePrice,
        configured_minimum_price: minimumPrice ?? 0,
        minimum_price_override: minimumPriceOverride,
        is_free_product: isFreeProduct,
        promotion_id: selectedPromotionId,
      })

      const refreshedSale = await fetchSale(currentSale.id)
      setSale(refreshedSale)
      setItems(refreshedSale.items)

      setProductId('')
      setQuantity(1)
      setSelectedPromotionId(null)
      setActualPriceInput('')
      setMinimumPriceOverride(false)
      setIsFreeProduct(false)
      setSuccess('Product added to the sale.')
    } catch (addError) {
      setError(
        addError instanceof Error
          ? addError.message
          : 'Unable to add the product.',
      )
    } finally {
      setAddingItem(false)
    }
  }

  async function handleReserveSale() {
    if (!sale) {
      setError('Create a sale before reserving it.')
      return
    }

    if (items.length === 0) {
      setError('Add at least one product before reserving the sale.')
      return
    }

    setReserving(true)
    setError('')
    setSuccess('')

    try {
      const reservedSale = await reserveSale(sale.id)
      const salePayments = await fetchSalePayments(sale.id)

      setSale(reservedSale)
      setItems(reservedSale.items)
      setPayments(salePayments)
      setPaymentAmount(
        Math.max(
          0,
          Number(reservedSale.payable_amount) -
            salePayments.reduce(
              (total, payment) => total + Number(payment.amount),
              0,
            ),
        ).toFixed(2),
      )
      setSuccess('Sale inventory reserved successfully.')
    } catch (reserveError) {
      setError(
        reserveError instanceof Error
          ? reserveError.message
          : 'Unable to reserve the sale.',
      )
    } finally {
      setReserving(false)
    }
  }

  async function handleAddPayment() {
    if (!sale || sale.status !== 'RESERVED') {
      setError('Payments can only be recorded for a reserved sale.')
      return
    }

    const amount = Number(paymentAmount)
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Enter a payment amount greater than zero.')
      return
    }

    if (paymentMode !== 'CASH' && !paymentReference.trim()) {
      setError('Enter the transaction/reference number for this payment mode.')
      return
    }

    setSavingPayment(true)
    setError('')
    setSuccess('')

    try {
      await addSalePayment(sale.id, {
        payment_mode: paymentMode,
        amount,
        transaction_reference: paymentReference.trim() || null,
      })
      const refreshedPayments = await fetchSalePayments(sale.id)
      const newPaidAmount = refreshedPayments.reduce(
        (total, payment) => total + Number(payment.amount),
        0,
      )
      setPayments(refreshedPayments)
      setPaymentAmount(
        Math.max(
          0,
          Number(sale.payable_amount) - newPaidAmount,
        ).toFixed(2),
      )
      setPaymentReference('')
      setSuccess('Offline payment recorded.')
    } catch (paymentError) {
      setError(
        paymentError instanceof Error
          ? paymentError.message
          : 'Unable to record payment.',
      )
    } finally {
      setSavingPayment(false)
    }
  }

  async function handleConfirmSale() {
    if (!sale || !isFullyPaid) {
      setError('Record the exact payable amount before confirming the sale.')
      return
    }

    setConfirming(true)
    setError('')
    setSuccess('')

    try {
      const confirmedSale = await confirmSale(sale.id)
      setSale(confirmedSale)
      setItems(confirmedSale.items)
      setSuccess('Sale confirmed and inventory marked as sold.')
    } catch (confirmError) {
      setError(
        confirmError instanceof Error
          ? confirmError.message
          : 'Unable to confirm the sale.',
      )
    } finally {
      setConfirming(false)
    }
  }

  async function handleDeliverSale() {
    if (!sale || sale.status !== 'CONFIRMED') {
      setError('Only confirmed sales can be delivered.')
      return
    }

    setDelivering(true)
    setError('')
    setSuccess('')

    try {
      const deliveredSale = await deliverSale(sale.id)
      setSale(deliveredSale)
      setItems(deliveredSale.items)
      setSuccess('Sale marked as delivered.')
    } catch (deliveryError) {
      setError(
        deliveryError instanceof Error
          ? deliveryError.message
          : 'Unable to deliver the sale.',
      )
    } finally {
      setDelivering(false)
    }
  }

  if (loading) {
    return (
      <section className="sales-page">
        <div className="loading-panel">
          Preparing your sales workspace...
        </div>
      </section>
    )
  }

  return (
    <section className="sales-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Transaction management</p>
          <h1>Sales</h1>
          <p>
            Create a sale using products and stores available to the
            authenticated employee.
          </p>
        </div>

        <button
          type="button"
          onClick={resetSale}
          disabled={
            sale !== null &&
            sale.status !== 'DRAFT' &&
            sale.status !== 'DELIVERED'
          }
        >
          + New Sale
        </button>
      </div>

      {error && (
        <div className="notice notice--error" role="alert">
          <strong>Something needs attention</strong>
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="notice notice--success" role="status">
          <strong>Success</strong>
          <span>{success}</span>
        </div>
      )}

      <div className="sales-workspace">
        <section className="form-section">
          <div className="section-header">
            <div>
              <h2>Sale Details</h2>
              <p>
                Select the selling store and the customer for the sale.
              </p>
            </div>

            <span className="status-badge">
              {sale?.status ?? 'DRAFT'}
            </span>
          </div>

          <div className="form-grid">
            <label>
              Store
              <select
                value={storeId}
                onChange={(event) => setStoreId(event.target.value)}
                disabled={sale !== null}
              >
                <option value="">Select store</option>

                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="form-grid">
            <div>
              <label>Customer</label>
              <div className="customer-selection" style={{ display: 'grid', gap: '0.75rem' }}>
                <div className="inline-actions" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    disabled={sale !== null}
                    onClick={() => {
                      setCustomerSelectionMode('walkin')
                      setCustomerId('')
                      setSelectedCustomer(null)
                      setCustomerQuery('')
                      setCustomerSearchResults([])
                    }}
                    className={customerSelectionMode === 'walkin' ? 'is-active' : ''}
                  >
                    Walk-in Customer
                  </button>

                  <button
                    type="button"
                    disabled={sale !== null}
                    onClick={() => {
                      setCustomerSelectionMode('existing')
                      setCustomerId('')
                      setSelectedCustomer(null)
                      setCustomerQuery('')
                      setCustomerSearchResults([])
                    }}
                    className={customerSelectionMode === 'existing' ? 'is-active' : ''}
                  >
                    Existing Customer
                  </button>

                  <button
                    type="button"
                    disabled={sale !== null}
                    onClick={() => {
                      setCustomerSelectionMode('new')
                      setCustomerId('')
                      setSelectedCustomer(null)
                      setCustomerQuery('')
                      setCustomerSearchResults([])
                    }}
                    className={customerSelectionMode === 'new' ? 'is-active' : ''}
                  >
                    New Customer
                  </button>
                </div>

                {customerSelectionMode === 'existing' && (
                  <>
                    <div className="search-row" style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        type="text"
                        value={customerQuery}
                        disabled={sale !== null}
                        placeholder="Search mobile number or customer name"
                        onChange={(event) => setCustomerQuery(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            void handleCustomerSearch()
                          }
                        }}
                      />
                      <button
                        type="button"
                        disabled={sale !== null}
                        onClick={() => void handleCustomerSearch()}
                      >
                        Search
                      </button>
                    </div>

                    {customerSearchResults.length > 0 ? (
                      <div className="customer-results" style={{ display: 'grid', gap: '0.5rem' }}>
                        {customerSearchResults.map((customer) => (
                          <button
                            type="button"
                            key={customer.id}
                            disabled={sale !== null}
                            className={customerId === String(customer.id) ? 'is-selected' : ''}
                            style={{ textAlign: 'left', padding: '0.5rem' }}
                            onClick={() => {
                              setCustomerId(String(customer.id))
                              setSelectedCustomer(customer)
                              setCustomerSelectionMode('existing')
                              setCustomerQuery(customer.name)
                              setCustomerSearchResults([])
                              setError('')
                            }}
                          >
                            {customer.name} — {customer.mobile}
                          </button>
                        ))}
                      </div>
                    ) : (
                      customerQuery.trim() && (
                        <div className="notice notice--warning">
                          <strong>Customer not found.</strong>
                          <span>Create a new customer to continue.</span>
                        </div>
                      )
                    )}
                  </>
                )}

                {customerSelectionMode === 'new' && (
                  <div className="customer-form" style={{ display: 'grid', gap: '0.75rem' }}>
                    <input
                      type="text"
                      disabled={sale !== null}
                      placeholder="Name"
                      value={newCustomerForm.name}
                      onChange={(event) =>
                        setNewCustomerForm((current) => ({
                          ...current,
                          name: event.target.value,
                        }))
                      }
                    />
                    <input
                      type="tel"
                      disabled={sale !== null}
                      placeholder="Mobile"
                      value={newCustomerForm.mobile}
                      onChange={(event) =>
                        setNewCustomerForm((current) => ({
                          ...current,
                          mobile: event.target.value,
                        }))
                      }
                    />
                    <input
                      type="email"
                      disabled={sale !== null}
                      placeholder="Email (optional)"
                      value={newCustomerForm.email}
                      onChange={(event) =>
                        setNewCustomerForm((current) => ({
                          ...current,
                          email: event.target.value,
                        }))
                      }
                    />
                    <input
                      type="text"
                      disabled={sale !== null}
                      placeholder="Address (optional)"
                      value={newCustomerForm.address}
                      onChange={(event) =>
                        setNewCustomerForm((current) => ({
                          ...current,
                          address: event.target.value,
                        }))
                      }
                    />
                    <button
                      type="button"
                      disabled={sale !== null}
                      onClick={() => void handleCreateCustomer()}
                    >
                      Create Customer
                    </button>
                  </div>
                )}

                {selectedCustomer && customerSelectionMode !== 'new' && (
                  <div className="selected-customer">
                    Selected customer: <strong>{selectedCustomer.name}</strong>
                    {selectedCustomer.mobile ? ` — ${selectedCustomer.mobile}` : ''}
                  </div>
                )}
              </div>
            </div>
          </div>

          {stores.length === 0 && (
            <div className="notice notice--error" role="alert">
              <strong>No store available</strong>
              <span>
                Your account does not currently have an active store
                available for sales.
              </span>
            </div>
          )}
        </section>

        <section className="form-section">
          <div className="section-header">
            <div>
              <h2>Add Product</h2>
              <p>
                Select a product to view availability, price, and the
                backend-authoritative sales rules.
              </p>
            </div>
          </div>

          <div className="form-grid">
            <label>
              Product
              <select
                value={productId}
                onChange={(event) => setProductId(event.target.value)}
                disabled={
                  !storeId ||
                  addingItem ||
                  !isSaleEditable
                }
              >
                <option value="">Select product</option>

                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} — {product.sku}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Quantity
              <input
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(event) =>
                  setQuantity(
                    Math.max(1, Number(event.target.value) || 1),
                  )
                }
                disabled={
                  addingItem || !isSaleEditable
                }
              />
            </label>
          </div>

          {selectedProduct && storeId && (
            <div className="product-preview" style={{ display: 'grid', gap: '0.75rem', marginTop: '1rem' }}>
              <div className="form-grid">
                <div>
                  <span>Product</span>
                  <strong>{selectedProduct.name}</strong>
                </div>
                <div>
                  <span>SKU</span>
                  <strong>{selectedProduct.sku}</strong>
                </div>
                <div>
                  <span>Selected Store</span>
                  <strong>{selectedStore?.name ?? '—'}</strong>
                </div>
                <div>
                  <span>Available</span>
                  <strong>
                    {selectedProductInventory?.available_quantity ?? 0}
                  </strong>
                </div>
                <div>
                  <span>Configured Sale Price</span>
                  <strong>
                    ₹{Number(configuredPrice || 0).toLocaleString('en-IN')}
                  </strong>
                </div>
                <div>
                  <span>Minimum Sale Price</span>
                  <strong>
                    {minimumPrice !== null
                      ? `₹${Number(minimumPrice).toLocaleString('en-IN')}`
                      : '—'}
                  </strong>
                </div>
              </div>

              <div className="form-grid">
                <label>
                  Actual Sale Price
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={actualPriceInput}
                    onChange={(event) => {
                      setMinimumPriceOverride(false)
                      setActualPriceInput(event.target.value)
                    }}
                    disabled={addingItem || !isSaleEditable}
                  />
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="checkbox"
                    checked={isFreeProduct}
                    onChange={(event) => {
                      setIsFreeProduct(event.target.checked)
                      if (event.target.checked) {
                        setMinimumPriceOverride(false)
                        setActualPriceInput('0')
                      } else {
                        setActualPriceInput(
                          String(selectedProductPrice?.sale_price ?? 0),
                        )
                      }
                    }}
                    disabled={addingItem || !isSaleEditable}
                  />
                  Free Product
                </label>
              </div>

              {minimumPrice !== null && !isFreeProduct && belowMinimumPrice && (
                <div className="notice notice--warning">
                  <strong>Minimum price rule.</strong>
                  <span>
                    Price is below the configured minimum selling price.
                  </span>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <input
                      type="checkbox"
                      checked={minimumPriceOverride}
                      onChange={(event) =>
                        setMinimumPriceOverride(event.target.checked)
                      }
                    />
                    I confirm this minimum-price override.
                  </label>
                </div>
              )}

              {availablePromotions.length > 0 && (
                <label>
                  Applicable offer / promotion
                  <select
                    value={selectedPromotionId ?? ''}
                    onChange={(event) =>
                      setSelectedPromotionId(
                        event.target.value ? Number(event.target.value) : null,
                      )
                    }
                    disabled={addingItem || !isSaleEditable}
                  >
                    <option value="">Select an offer</option>
                    {availablePromotions.map((promotion) => (
                      <option key={promotion.id} value={promotion.id}>
                          {promotion.name}
                          {promotion.cashback_amount > 0
                            ? ` — UPI cashback ₹${Number(promotion.cashback_amount).toLocaleString('en-IN')}`
                            : ''}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <div className="form-actions">
                <button
                  type="button"
                  onClick={() => void handleAddProduct()}
                  disabled={
                    addingItem ||
                    !storeId ||
                    !selectedProduct ||
                    !isSaleEditable
                  }
                >
                  {addingItem ? 'Adding...' : 'Add Product'}
                </button>
              </div>
            </div>
          )}
        </section>

        <section className="form-section">
          <div className="section-header">
            <div>
              <h2>Sale Items</h2>
              <p>
                Product details, price, GST, offer visibility, and line totals.
              </p>
            </div>

            {sale && (
              <span>
                Sale ID: <strong>#{sale.id}</strong>
              </span>
            )}
          </div>

          {items.length === 0 ? (
            <div className="empty-state">
              <h3>No products added</h3>
              <p>
                Select a product and quantity above to add it to the sale.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Qty</th>
                    <th>Configured Price</th>
                    <th>Actual Price</th>
                    <th>GST</th>
                    <th>Discount</th>
                    <th>Promotion</th>
                    <th>Line Total</th>
                    <th>Free</th>
                  </tr>
                </thead>

                <tbody>
                  {items.map((item) => {
                    const product = productMap.get(item.product_id)

                    return (
                      <tr key={item.id}>
                        <td>{product?.name ?? `Product ${item.product_id}`}</td>
                        <td>{product?.sku ?? '—'}</td>
                        <td>{item.quantity}</td>
                        <td>₹{Number(item.configured_unit_price).toLocaleString('en-IN')}</td>
                        <td>₹{Number(item.actual_unit_price).toLocaleString('en-IN')}</td>
                        <td>₹{Number(item.gst_amount).toLocaleString('en-IN')}</td>
                        <td>
                          {item.discount_amount > 0
                            ? `₹${Number(item.discount_amount).toLocaleString('en-IN')}`
                            : '—'}
                        </td>
                        <td>{item.promotion_name ?? '—'}</td>
                        <td>₹{Number(item.line_total).toLocaleString('en-IN')}</td>
                        <td>{item.is_free_product ? 'FREE' : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {sale && (
          <section className="form-section">
            <div className="section-header">
              <div>
                <h2>Sale Summary</h2>
                <p>Totals are supplied by the backend and remain authoritative.</p>
              </div>
            </div>

            <div className="summary-grid">
              <div>
                <span>Subtotal</span>
                <strong>₹{Number(sale.subtotal).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>Invoice Discount</span>
                <strong>₹{Number(sale.invoice_discount).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>Taxable Amount</span>
                <strong>₹{Number(sale.taxable_amount).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>GST</span>
                <strong>₹{Number(sale.gst_amount).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>Total</span>
                <strong>₹{Number(sale.total_amount).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>UPI Cashback</span>
                <strong>−₹{Number(sale.cashback_amount).toLocaleString('en-IN')}</strong>
              </div>

              <div>
                <span>Payable</span>
                <strong>₹{Number(sale.payable_amount).toLocaleString('en-IN')}</strong>
              </div>
            </div>

            <div className="form-actions">
              {sale.status === 'DRAFT' && (
                <button
                  type="button"
                  onClick={() => void handleReserveSale()}
                  disabled={reserving || items.length === 0}
                >
                  {reserving ? 'Reserving...' : 'Reserve Sale'}
                </button>
              )}

              {sale.status === 'CONFIRMED' && (
                <button
                  type="button"
                  onClick={() => void handleDeliverSale()}
                  disabled={delivering}
                >
                  {delivering ? 'Delivering...' : 'Mark Delivered'}
                </button>
              )}
            </div>
          </section>
        )}

        {sale?.status === 'RESERVED' && (
          <section className="form-section">
            <div className="section-header">
              <div>
                <h2>Offline Payment</h2>
                <p>Record one or more payments against the payable amount.</p>
              </div>
            </div>

            <div className="summary-grid">
              <div>
                <span>Paid</span>
                <strong>₹{paidAmount.toLocaleString('en-IN')}</strong>
              </div>
              <div>
                <span>Remaining</span>
                <strong>₹{remainingPayable.toLocaleString('en-IN')}</strong>
              </div>
            </div>

            <div className="form-grid">
              <label>
                Payment Mode
                <select
                  value={paymentMode}
                  onChange={(event) => setPaymentMode(event.target.value)}
                  disabled={savingPayment || remainingPayable === 0}
                >
                  <option value="CASH">Cash</option>
                  <option value="UPI">UPI</option>
                  <option value="CARD">Card</option>
                  <option value="BANK_TRANSFER">Bank Transfer</option>
                  <option value="CHEQUE">Cheque</option>
                </select>
              </label>
              <label>
                Amount
                <input
                  type="number"
                  min="0.01"
                  max={remainingPayable}
                  step="0.01"
                  value={paymentAmount}
                  onChange={(event) => setPaymentAmount(event.target.value)}
                  disabled={savingPayment || remainingPayable === 0}
                />
              </label>
              {paymentMode !== 'CASH' && (
                <label>
                  Transaction / Reference Number
                  <input
                    type="text"
                    required
                    value={paymentReference}
                    onChange={(event) => setPaymentReference(event.target.value)}
                    disabled={savingPayment || remainingPayable === 0}
                  />
                </label>
              )}
            </div>

            <div className="form-actions">
              <button
                type="button"
                onClick={() => void handleAddPayment()}
                disabled={savingPayment || remainingPayable === 0}
              >
                {savingPayment ? 'Recording...' : 'Record Payment'}
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmSale()}
                disabled={confirming || !isFullyPaid}
              >
                {confirming ? 'Confirming...' : 'Confirm Sale'}
              </button>
            </div>

            {sale.cashback_amount > 0 &&
              !payments.some(
                (payment) => payment.payment_mode.toUpperCase() === 'UPI',
              ) && (
                <div className="notice notice--warning" role="status">
                  <strong>UPI payment required for cashback.</strong>
                  <span>Record at least one UPI payment before confirmation.</span>
                </div>
              )}

            {payments.length > 0 && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Mode</th>
                      <th>Amount</th>
                      <th>Reference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>{payment.payment_mode}</td>
                        <td>₹{Number(payment.amount).toLocaleString('en-IN')}</td>
                        <td>{payment.transaction_reference ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </section>
  )
}