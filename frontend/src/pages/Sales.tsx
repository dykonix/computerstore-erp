import { useMemo, useState } from 'react'

type Product = {
  id: number
  name: string
  price: number
}

type SaleItem = {
  id: number
  productId: number
  productName: string
  quantity: number
  unitPrice: number
}

const products: Product[] = [
  { id: 1, name: 'HP Laptop', price: 50000 },
  { id: 2, name: 'Dell Laptop', price: 55000 },
  { id: 3, name: 'Lenovo Laptop', price: 48000 },
]

const stores = [
  { id: 1, name: 'Mahamaya Computers' },
  { id: 2, name: 'HP World SBP' },
  { id: 3, name: 'HP World JSG' },
]

const customers = [
  { id: 1, name: 'Walk-in Customer', mobile: '' },
  { id: 2, name: 'Demo Customer', mobile: '9999999999' },
]

export default function Sales() {
  const [isNewSale, setIsNewSale] = useState(false)
  const [storeId, setStoreId] = useState('')
  const [customerId, setCustomerId] = useState('')
  const [productId, setProductId] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [items, setItems] = useState<SaleItem[]>([])
  const [invoiceDiscount, setInvoiceDiscount] = useState(0)

  const selectedProduct = products.find(
    (product) => product.id === Number(productId),
  )

  function handleNewSale() {
    setIsNewSale(true)
    setStoreId('')
    setCustomerId('')
    setProductId('')
    setQuantity(1)
    setItems([])
    setInvoiceDiscount(0)
  }

  function handleAddProduct() {
    if (!selectedProduct || quantity <= 0) {
      return
    }

    setItems((currentItems) => {
      const existingItem = currentItems.find(
        (item) => item.productId === selectedProduct.id,
      )

      if (existingItem) {
        return currentItems.map((item) =>
          item.productId === selectedProduct.id
            ? { ...item, quantity: item.quantity + quantity }
            : item,
        )
      }

      return [
        ...currentItems,
        {
          id: Date.now(),
          productId: selectedProduct.id,
          productName: selectedProduct.name,
          quantity,
          unitPrice: selectedProduct.price,
        },
      ]
    })

    setProductId('')
    setQuantity(1)
  }

  function handleRemoveItem(itemId: number) {
    setItems((currentItems) =>
      currentItems.filter((item) => item.id !== itemId),
    )
  }

  const subtotal = useMemo(
    () =>
      items.reduce(
        (total, item) => total + item.quantity * item.unitPrice,
        0,
      ),
    [items],
  )

  const taxableAmount = Math.max(subtotal - invoiceDiscount, 0)
  const gstAmount = taxableAmount * 0.18
  const totalAmount = taxableAmount + gstAmount

  return (
    <section className="sales-page">
      <div className="page-header">
        <div>
          <h1>Sales</h1>
          <p>Create and manage customer sales.</p>
        </div>

        {!isNewSale && (
          <button type="button" onClick={handleNewSale}>
            + New Sale
          </button>
        )}
      </div>

      {!isNewSale ? (
        <div className="empty-state">
          <h2>No sale selected</h2>
          <p>Start a new sale to begin adding products.</p>
          <button type="button" onClick={handleNewSale}>
            + New Sale
          </button>
        </div>
      ) : (
        <div className="sales-workspace">
          <section className="form-section">
            <div className="section-header">
              <div>
                <h2>New Sale</h2>
                <p>Start by selecting the selling store and customer.</p>
              </div>

              <span className="status-badge">DRAFT</span>
            </div>

            <div className="form-grid">
              <label>
                Store
                <select
                  value={storeId}
                  onChange={(event) => setStoreId(event.target.value)}
                >
                  <option value="">Select store</option>
                  {stores.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Customer
                <select
                  value={customerId}
                  onChange={(event) => setCustomerId(event.target.value)}
                >
                  <option value="">Select customer</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                      {customer.mobile ? ` - ${customer.mobile}` : ''}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="form-section">
            <div className="section-header">
              <div>
                <h2>Add Product</h2>
                <p>Select a product and quantity to add it to the sale.</p>
              </div>
            </div>

            <div className="product-entry">
              <label>
                Product
                <select
                  value={productId}
                  onChange={(event) => setProductId(event.target.value)}
                >
                  <option value="">Select product</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name} - ₹{product.price.toLocaleString('en-IN')}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Quantity
                <input
                  type="number"
                  min="1"
                  value={quantity}
                  onChange={(event) =>
                    setQuantity(Math.max(1, Number(event.target.value)))
                  }
                />
              </label>

              <button
                type="button"
                onClick={handleAddProduct}
                disabled={!selectedProduct}
              >
                Add Product
              </button>
            </div>
          </section>

          <section className="form-section">
            <div className="section-header">
              <div>
                <h2>Items</h2>
                <p>Products currently included in this sale.</p>
              </div>
            </div>

            {items.length === 0 ? (
              <div className="empty-items">
                No products added yet.
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Quantity</th>
                      <th>Unit Price</th>
                      <th>Line Total</th>
                      <th />
                    </tr>
                  </thead>

                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td>{item.productName}</td>
                        <td>{item.quantity}</td>
                        <td>
                          ₹{item.unitPrice.toLocaleString('en-IN')}
                        </td>
                        <td>
                          ₹
                          {(item.quantity * item.unitPrice).toLocaleString(
                            'en-IN',
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(item.id)}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="sale-summary">
            <div className="summary-row">
              <span>Subtotal</span>
              <strong>₹{subtotal.toLocaleString('en-IN')}</strong>
            </div>

            <div className="summary-row">
              <label htmlFor="invoice-discount">
                Invoice Discount
              </label>
              <input
                id="invoice-discount"
                type="number"
                min="0"
                max={subtotal}
                value={invoiceDiscount}
                onChange={(event) =>
                  setInvoiceDiscount(
                    Math.min(
                      subtotal,
                      Math.max(0, Number(event.target.value)),
                    ),
                  )
                }
              />
            </div>

            <div className="summary-row">
              <span>Taxable Amount</span>
              <strong>
                ₹{taxableAmount.toLocaleString('en-IN')}
              </strong>
            </div>

            <div className="summary-row">
              <span>GST</span>
              <strong>₹{gstAmount.toLocaleString('en-IN')}</strong>
            </div>

            <div className="summary-row total-row">
              <span>Total</span>
              <strong>₹{totalAmount.toLocaleString('en-IN')}</strong>
            </div>
          </section>

          <section className="sale-actions">
            <button
              type="button"
              onClick={() => setIsNewSale(false)}
            >
              Cancel
            </button>

            <button type="button" disabled>
              Save Draft
            </button>

            <button
              type="button"
              disabled
              title="Connect after the sale creation API is implemented"
            >
              Reserve Sale
            </button>
          </section>
        </div>
      )}
    </section>
  )
}