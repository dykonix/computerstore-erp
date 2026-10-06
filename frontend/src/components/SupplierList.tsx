import type { Supplier } from '../api/supplierApi'

interface SupplierListProps {
  suppliers: Supplier[]
  loading: boolean
  onEdit: (supplierId: number) => void
  editingSupplierId: number | null
}

export default function SupplierList({ suppliers, loading, onEdit, editingSupplierId }: SupplierListProps) {
  return (
    <section className="product-list-panel">
      <div className="section-heading section-heading--list">
        <div>
          <p className="eyebrow">Directory</p>
          <h2>Supplier list</h2>
        </div>
        <span>{suppliers.length} records</span>
      </div>
      {loading ? <div className="table-loading">Loading suppliers...</div> : suppliers.length === 0 ? (
        <div className="empty-state">No suppliers yet. Add your first supplier above.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Supplier name</th><th>Contact person</th><th>Phone</th><th>Email</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td className="product-name-cell">{supplier.name}</td>
                  <td>{supplier.contact_person || '—'}</td>
                  <td>{supplier.phone || '—'}</td>
                  <td>{supplier.email || '—'}</td>
                  <td><span className={`status-pill ${supplier.is_active ? 'status-pill--active' : ''}`}>{supplier.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td><button type="button" className="row-action" onClick={() => onEdit(supplier.id)} disabled={editingSupplierId === supplier.id}>{editingSupplierId === supplier.id ? 'Loading' : 'Edit'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}