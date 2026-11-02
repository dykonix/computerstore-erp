import { useEffect, useMemo, useState } from 'react'
import {
  createProduct,
  createProductPrice,
  fetchCurrentProductPrice,
  fetchProduct,
  fetchProductFormData,
  fetchProducts,
  updateProduct,
  updateProductPrice,
} from '../api/productApi'
import type { ProductCreateRequest, ProductFormData, ProductListItem, ProductPriceResponse, ProductPriceWriteRequest, ProductResponse } from '../api/productApi'
import ProductForm from '../components/ProductForm'
import ProductList from '../components/ProductList'
import '../ProductMaster.css'

export default function ProductMaster() {
  const [formData, setFormData] = useState<ProductFormData | null>(null)
  const [products, setProducts] = useState<ProductListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [listLoading, setListLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingProduct, setEditingProduct] = useState<ProductResponse | null>(null)
  const [editingPrice, setEditingPrice] = useState<ProductPriceResponse | null>(null)
  const [editingProductId, setEditingProductId] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [brandFilter, setBrandFilter] = useState('all')
  const [expandedProductId, setExpandedProductId] = useState<number | null>(null)
  const [prices, setPrices] = useState<Record<number, ProductPriceResponse | null>>({})

  async function loadProducts() {
    setListLoading(true)
    try {
      const response = await fetchProducts({ page: 1, pageSize: 100 })
      setProducts(response.items)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load products.')
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const [nextFormData] = await Promise.all([fetchProductFormData(), loadProducts()])
        setFormData(nextFormData)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load product form data.')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const filteredProducts = useMemo(() => products.filter((product) => {
    const term = search.trim().toLowerCase()
    const matchesSearch = !term || [product.name, product.sku, product.brand.name, product.category.name]
      .some((value) => value.toLowerCase().includes(term))
    return matchesSearch && (categoryFilter === 'all' || String(product.category.id) === categoryFilter)
      && (brandFilter === 'all' || String(product.brand.id) === brandFilter)
  }), [products, search, categoryFilter, brandFilter])
  const visibleProducts = filteredProducts.slice(0, 5)

  useEffect(() => {
    let cancelled = false
    async function loadVisiblePrices() {
      const missing = visibleProducts.filter((product) => !(product.id in prices))
      if (!missing.length) return
      const results = await Promise.all(missing.map(async (product) => {
        try { return [product.id, await fetchCurrentProductPrice(product.id)] as const }
        catch { return [product.id, null] as const }
      }))
      if (!cancelled) setPrices((current) => {
        const next = { ...current }
        results.forEach(([id, price]) => { next[id] = price })
        return next
      })
    }
    void loadVisiblePrices()
    return () => { cancelled = true }
  }, [visibleProducts, prices])

  async function handleSubmit(payload: { product: ProductCreateRequest; pricing: ProductPriceWriteRequest }) {
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      if (editingProduct) {
        await updateProduct(editingProduct.id, payload.product)
        if (editingPrice) await updateProductPrice(editingProduct.id, editingPrice.id, payload.pricing)
        else await createProductPrice(editingProduct.id, payload.pricing)
        setSuccess('Product updated successfully.')
      } else {
        const product = await createProduct(payload.product)
        await createProductPrice(product.id, payload.pricing)
        setSuccess('Product created successfully.')
      }
      setFormOpen(false)
      setEditingProduct(null)
      setEditingPrice(null)
      await loadProducts()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save product.')
      throw submitError
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEdit(productId: number) {
    setError('')
    setSuccess('')
    setEditingProductId(productId)
    try {
      const [product, price] = await Promise.all([fetchProduct(productId), fetchCurrentProductPrice(productId)])
      setEditingProduct(product)
      setEditingPrice(price)
      setFormOpen(true)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load product.')
    } finally {
      setEditingProductId(null)
    }
  }

  function handleCreateClick() {
    setEditingProduct(null)
    setEditingPrice(null)
    setError('')
    setSuccess('')
    setFormOpen(true)
  }

  function handleCancelForm() {
    setFormOpen(false)
    setEditingProduct(null)
    setEditingPrice(null)
  }

  return (
    <div className="product-page catalog-page">
      <header className="catalog-header">
        <div>
          <p className="eyebrow">Product catalog</p>
          <h1>Products</h1>
          <p className="page-description">Manage product configurations, pricing and stock availability.</p>
        </div>
        <button type="button" className="primary-button catalog-create-button" onClick={handleCreateClick}>＋ <span>Create Product</span></button>
      </header>

      {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
      {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}

      {formOpen && (loading || !formData ? <div className="loading-panel">Preparing product form...</div> : (
        <section className="catalog-form-shell" aria-label={editingProduct ? 'Edit product' : 'Create product'}>
          <div className="catalog-form-heading">
            <div><p className="eyebrow">Product details</p><h2>{editingProduct ? 'Edit Product' : 'Create Product'}</h2></div>
            <button type="button" className="secondary-button" onClick={handleCancelForm}>Close</button>
          </div>
          <ProductForm key={editingProduct?.id ?? 'create'} {...formData} options={formData.attribute_options} categoryAttributes={formData.category_attributes} submitting={submitting} editingProduct={editingProduct} editingPrice={editingPrice} onSubmit={handleSubmit} onCancelEdit={handleCancelForm} />
        </section>
      ))}

      <ProductList
        products={visibleProducts}
        totalFiltered={filteredProducts.length}
        totalProducts={products.length}
        loading={loading || listLoading}
        search={search}
        categoryFilter={categoryFilter}
        brandFilter={brandFilter}
        categories={formData?.categories ?? []}
        brands={formData?.brands ?? []}
        prices={prices}
        expandedProductId={expandedProductId}
        onSearchChange={setSearch}
        onCategoryChange={setCategoryFilter}
        onBrandChange={setBrandFilter}
        onToggleAvailability={(productId) => setExpandedProductId((current) => current === productId ? null : productId)}
        onEdit={handleEdit}
        editingProductId={editingProductId}
      />
    </div>
  )
}
