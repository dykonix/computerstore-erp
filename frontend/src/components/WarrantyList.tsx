import type { WarrantyOption } from '../api/warrantyApi'

interface WarrantyListProps {
  options: WarrantyOption[]
  loading: boolean
  selectedOptionId: number | null
  editingOptionId: number | null
  statusUpdatingId: number | null
  onSelectPrices: (option: WarrantyOption) => void
  onEdit: (optionId: number) => void
  onToggleStatus: (option: WarrantyOption) => void
}

export default function WarrantyList({
  options,
  loading,
  selectedOptionId,
  editingOptionId,
  statusUpdatingId,
  onSelectPrices,
  onEdit,
  onToggleStatus,
}: WarrantyListProps) {
  return (
    <section className="product-list-panel">
      <div className="section-heading section-heading--list">
        <div>
          <p className="eyebrow">Product coverage</p>
          <h2>Warranty options</h2>
        </div>
        <span>{options.length} records</span>
      </div>
      {loading ? <div className="table-loading">Loading warranty options...</div> : options.length === 0 ? (
        <div className="empty-state">No warranty options for this product yet.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Additional coverage</th><th>Status</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {options.map((option) => (
                <tr key={option.id} className={selectedOptionId === option.id ? 'selected-row' : undefined}>
                  <td className="product-name-cell">{option.additional_months} months</td>
                  <td><span className={`status-pill ${option.is_active ? 'status-pill--active' : ''}`}>{option.is_active ? 'Active' : 'Inactive'}</span></td>
                  <td className="category-actions">
                    <button type="button" className="row-action" onClick={() => onSelectPrices(option)}>{selectedOptionId === option.id ? 'Pricing selected' : 'Prices'}</button>
                    <button type="button" className="row-action" onClick={() => onEdit(option.id)} disabled={editingOptionId === option.id || statusUpdatingId === option.id}>{editingOptionId === option.id ? 'Loading' : 'Edit'}</button>
                    <button type="button" className="row-action" onClick={() => onToggleStatus(option)} disabled={statusUpdatingId === option.id || editingOptionId === option.id}>{statusUpdatingId === option.id ? 'Saving' : option.is_active ? 'Deactivate' : 'Activate'}</button>
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