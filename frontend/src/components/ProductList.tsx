import { Fragment, useEffect, useState } from 'react'
import type { Brand, Category, ProductListItem, ProductPriceResponse } from '../api/productApi'
import { fetchInventory } from '../api/inventoryApi'
import type { InventoryItem } from '../api/inventoryApi'

interface ProductListProps {
  products: ProductListItem[]
  totalFiltered: number
  totalProducts: number
  loading: boolean
  search: string
  categoryFilter: string
  brandFilter: string
  categories: Category[]
  brands: Brand[]
  prices: Record<number, ProductPriceResponse | null>
  expandedProductId: number | null
  onSearchChange: (value: string) => void
  onCategoryChange: (value: string) => void
  onBrandChange: (value: string) => void
  onToggleAvailability: (productId: number) => void
  onEdit: (productId: number) => void
  editingProductId: number | null
}

function formatCurrency(value: number | null | undefined) {
  if (value == null || !Number.isFinite(Number(value))) return '—'
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value))
}

function ProductAvailability({ productId }: { productId: number }) {
  const [items, setItems] = useState<InventoryItem[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let cancelled = false
    setItems(null)
    setError('')
    fetchInventory(productId).then((response) => {
      if (!cancelled) setItems(response.items)
    }).catch((loadError: unknown) => {
      if (!cancelled) setError(loadError instanceof Error ? loadError.message : 'Unable to load stock availability.')
    })
    return () => { cancelled = true }
  }, [productId])

  if (error) return <div className="availability-message" role="alert">{error}</div>
  if (items === null) return <div className="availability-message">Loading stock availability…</div>
  if (!items.length) return <div className="availability-message">No inventory balances recorded for this product.</div>

  return (
    <div className="availability-table-wrap">
      <table className="availability-table">
        <thead><tr><th>Location</th><th>Type</th><th>On-hand</th><th>Reserved</th><th>Available</th></tr></thead>
        <tbody>{items.map((item) => (
          <tr key={item.id}>
            <td>{item.location.name}</td><td>{item.location.type}</td><td>{item.quantity}</td>
            <td className={item.reserved_quantity > 0 ? 'reserved-value' : ''}>{item.reserved_quantity}</td>
            <td className="available-value">{item.available_quantity}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  )
}

export default function ProductList({
  products, totalFiltered, totalProducts, loading, search, categoryFilter, brandFilter,
  categories, brands, prices, expandedProductId, onSearchChange, onCategoryChange,
  onBrandChange, onToggleAvailability, onEdit, editingProductId,
}: ProductListProps) {
  return (
    <section className="product-list-panel catalog-list-panel">
      <div className="catalog-toolbar">
        <label className="catalog-search"><span className="catalog-search-icon" aria-hidden="true">⌕</span><input value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Search product name, model or SKU" aria-label="Search product name, model or SKU" /></label>
        <label className="catalog-filter"><span>Category</span><select value={categoryFilter} onChange={(event) => onCategoryChange(event.target.value)}><option value="all">All categories</option>{categories.map((category) => <option key={category.id} value={String(category.id)}>{category.name}</option>)}</select></label>
        <label className="catalog-filter"><span>Brand</span><select value={brandFilter} onChange={(event) => onBrandChange(event.target.value)}><option value="all">All brands</option>{brands.map((brand) => <option key={brand.id} value={String(brand.id)}>{brand.name}</option>)}</select></label>
        <span className="catalog-count">Showing {products.length} of {totalFiltered} products{totalProducts !== totalFiltered ? ` · ${totalProducts} total` : ''}</span>
      </div>
      {loading ? <div className="table-loading catalog-empty">Loading products…</div> : products.length === 0 ? <div className="empty-state catalog-empty">No products match your search and filters.</div> : (
        <div className="table-wrap">
          <table className="catalog-table">
            <thead><tr><th className="catalog-expand-heading"></th><th>Product</th><th>Category</th><th>Brand</th><th>Sale price</th><th>Action</th></tr></thead>
            <tbody>{products.map((product) => {
              const expanded = expandedProductId === product.id
              const price = prices[product.id]
              return <Fragment key={product.id}>
                <tr className={`catalog-product-row ${expanded ? 'catalog-product-row--expanded' : ''}`}>
                  <td className="catalog-expand-cell"><button type="button" className="catalog-expand-button" onClick={() => onToggleAvailability(product.id)} aria-expanded={expanded} aria-label={`${expanded ? 'Hide' : 'Show'} stock availability for ${product.name}`}>{expanded ? '⌄' : '›'}</button></td>
                  <td><button type="button" className="catalog-product-trigger" onClick={() => onToggleAvailability(product.id)} aria-expanded={expanded}><span className="catalog-product-thumbnail" aria-hidden="true">{product.category.name.toLowerCase().includes('printer') ? '▤' : product.category.name.toLowerCase().includes('desktop') ? '▣' : '▱'}</span><span className="catalog-product-copy"><strong>{product.name}</strong><span>{product.brand.name} {product.category.name}</span><small>SKU: {product.sku || '—'}</small></span></button></td>
                  <td>{product.category.name}</td><td>{product.brand.name}</td><td className="catalog-price">{price === undefined ? 'Loading…' : formatCurrency(price?.sale_price)}</td>
                  <td><button type="button" className="catalog-edit-button" onClick={() => onEdit(product.id)} disabled={editingProductId === product.id}>{editingProductId === product.id ? 'Loading…' : 'Edit'}</button></td>
                </tr>
                {expanded && <tr key={`${product.id}-availability`} className="catalog-availability-row"><td colSpan={6}><ProductAvailability productId={product.id} /></td></tr>}
              </Fragment>
            })}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
