import { useEffect, useState } from 'react'
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

  async function loadProducts() {
    setListLoading(true)
    try {
      const response = await fetchProducts()
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

  async function handleSubmit(payload: { product: ProductCreateRequest; pricing: ProductPriceWriteRequest }) {
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      if (editingProduct) {
        await updateProduct(editingProduct.id, payload.product)
        if (editingPrice) {
          await updateProductPrice(editingProduct.id, editingPrice.id, payload.pricing)
        } else {
          await createProductPrice(editingProduct.id, payload.pricing)
        }
        setSuccess('Product updated successfully.')
        setEditingProduct(null)
        setEditingPrice(null)
      } else {
        const product = await createProduct(payload.product)
        await createProductPrice(product.id, payload.pricing)
        setSuccess('Product created successfully.')
      }
      await loadProducts()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to create product.')
      throw submitError
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEdit(productId: number) {
    setError('')
    setSuccess('')
    setEditingProductId(productId)
    setEditingProduct(null)
    setEditingPrice(null)
    try {
      const [product, price] = await Promise.all([
        fetchProduct(productId),
        fetchCurrentProductPrice(productId),
      ])
      setEditingProduct(product)
      setEditingPrice(price)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load product.')
    } finally {
      setEditingProductId(null)
    }
  }

  return (
    <div className="product-page">
      <div className="page-intro">
        <div>
          <p className="eyebrow">Inventory foundation</p>
          <h1>Product Master</h1>
          <p className="page-description">Create sellable configurations and manage the catalog your team works from.</p>
        </div>
        <div className="page-mark">PM<span>01</span></div>
      </div>
      {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
      {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
      {loading || !formData ? (
        <div className="loading-panel">Preparing your product workspace...</div>
      ) : (
        <>
          <ProductForm key={editingProduct?.id ?? 'create'} {...formData} options={formData.attribute_options} categoryAttributes={formData.category_attributes} submitting={submitting} editingProduct={editingProduct} editingPrice={editingPrice} onSubmit={handleSubmit} onCancelEdit={() => { setEditingProduct(null); setEditingPrice(null) }} />
          <ProductList products={products} loading={listLoading} onEdit={handleEdit} editingProductId={editingProductId} />
        </>
      )}
    </div>
  )
}