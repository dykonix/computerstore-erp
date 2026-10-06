import type { ProductListItem } from '../api/productApi'

interface ProductListProps {
  products: ProductListItem[]
  loading: boolean
  onEdit: (productId: number) => void
  editingProductId: number | null
}

export default function ProductList({ products, loading, onEdit, editingProductId }: ProductListProps) {
  return (
    <section className="product-list-panel">
      <div className="section-heading section-heading--list">
        <div>
          <p className="eyebrow">Catalog</p>
          <h2>Product master</h2>
        </div>
        <span>{products.length} records</span>
      </div>
      {loading ? <div className="table-loading">Loading products...</div> : products.length === 0 ? <div className="empty-state">No products yet. Create the first configuration above.</div> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>SKU</th><th>Product name</th><th>Category</th><th>Brand</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id}>
                  <td className="mono">{product.sku}</td>
                  <td className="product-name-cell">{product.name}</td>
                  <td>{product.category.name}</td>
                  <td>{product.brand.name}</td>
                  <td><span className={`status-pill ${product.is_active ? 'status-pill--active' : ''}`}>{product.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td><button type="button" className="row-action" onClick={() => onEdit(product.id)} disabled={editingProductId === product.id}>{editingProductId === product.id ? 'Editing' : 'Edit'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}