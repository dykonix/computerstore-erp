import type { Category } from '../api/categoryApi'

interface CategoryListProps {
  categories: Category[]
  loading: boolean
  onEdit: (categoryId: number) => void
  onToggleStatus: (category: Category) => void
  editingCategoryId: number | null
  statusUpdatingId: number | null
}

export default function CategoryList({
  categories,
  loading,
  onEdit,
  onToggleStatus,
  editingCategoryId,
  statusUpdatingId,
}: CategoryListProps) {
  return (
    <section className="product-list-panel">
      <div className="section-heading section-heading--list">
        <div>
          <p className="eyebrow">Catalog setup</p>
          <h2>Category list</h2>
        </div>
        <span>{categories.length} records</span>
      </div>
      {loading ? <div className="table-loading">Loading categories...</div> : categories.length === 0 ? (
        <div className="empty-state">No categories yet. Add the first category above.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Category name</th><th>Description</th><th>GST rate</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category.id}>
                  <td className="product-name-cell">{category.name}</td>
                  <td>{category.description || '—'}</td>
                  <td>{category.gst_rate === null ? '—' : `${category.gst_rate}%`}</td>
                  <td><span className={`status-pill ${category.is_active ? 'status-pill--active' : ''}`}>{category.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="category-actions">
                    <button type="button" className="row-action" onClick={() => onEdit(category.id)} disabled={editingCategoryId === category.id || statusUpdatingId === category.id}>
                      {editingCategoryId === category.id ? 'Loading' : 'Edit'}
                    </button>
                    <button type="button" className="row-action" onClick={() => onToggleStatus(category)} disabled={statusUpdatingId === category.id || editingCategoryId === category.id}>
                      {statusUpdatingId === category.id ? 'Saving' : category.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}