import { useState } from 'react'
import type { FormEvent } from 'react'
import type { ProductListItem } from '../api/productApi'
import type { WarrantyOption } from '../api/warrantyApi'

export interface WarrantyOptionFormData {
  product_id: number
  additional_months: number
  is_active: boolean
}

interface WarrantyFormProps {
  products: ProductListItem[]
  selectedProductId: string
  submitting: boolean
  editingOption: WarrantyOption | null
  onProductChange: (productId: string) => void
  onSubmit: (payload: WarrantyOptionFormData) => Promise<void>
  onCancelEdit: () => void
}

export default function WarrantyForm({
  products,
  selectedProductId,
  submitting,
  editingOption,
  onProductChange,
  onSubmit,
  onCancelEdit,
}: WarrantyFormProps) {
  const [additionalMonths, setAdditionalMonths] = useState(() => editingOption?.additional_months.toString() ?? '')
  const [isActive, setIsActive] = useState(() => editingOption?.is_active ?? true)
  const [errors, setErrors] = useState<Record<string, string>>({})

  function selectProduct(value: string) {
    onProductChange(value)
  }

  function reset() {
    onProductChange('')
    setAdditionalMonths('')
    setIsActive(true)
    setErrors({})
    onProductChange('')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const months = Number(additionalMonths)
    const nextErrors: Record<string, string> = {}
    if (!selectedProductId) nextErrors.product = 'Choose a product.'
    if (!Number.isInteger(months) || months <= 0) {
      nextErrors.months = 'Additional months must be a positive whole number.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    await onSubmit({ product_id: Number(selectedProductId), additional_months: months, is_active: isActive })
    if (!editingOption) reset()
  }

  return (
    <form className="product-form" onSubmit={submit} noValidate>
      <div className="form-heading">
        <div>
          <p className="eyebrow">{editingOption ? 'Warranty details' : 'New warranty option'}</p>
          <h2>{editingOption ? 'Update warranty option' : 'Add a warranty option'}</h2>
        </div>
        <span className="required-note"><b>*</b> Required</span>
      </div>

      <div className="form-grid form-grid--base warranty-form-grid">
        <label className={errors.product ? 'has-error' : ''}>
          <span>Product <b>*</b></span>
          <select
            value={selectedProductId}
            disabled={Boolean(editingOption)}
            onChange={(event) => selectProduct(event.target.value)}
          >
            <option value="">Select product</option>
            {products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
          </select>
          {errors.product && <small>{errors.product}</small>}
        </label>
        <label className={errors.months ? 'has-error' : ''}>
          <span>Additional months <b>*</b></span>
          <input
            type="number"
            min="1"
            step="1"
            value={additionalMonths}
            onChange={(event) => {
              setAdditionalMonths(event.target.value)
              setErrors((current) => ({ ...current, months: '' }))
            }}
            placeholder="e.g. 12"
            aria-invalid={Boolean(errors.months)}
          />
          {errors.months && <small>{errors.months}</small>}
        </label>
        <label>
          <span>Status</span>
          <select value={isActive ? 'active' : 'inactive'} onChange={(event) => setIsActive(event.target.value === 'active')}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </label>
      </div>

      <div className="form-actions">
        {editingOption && <button type="button" className="secondary-button" onClick={onCancelEdit} disabled={submitting}>Cancel edit</button>}
        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? 'Saving...' : editingOption ? 'Update Warranty Option' : 'Create Warranty Option'}
        </button>
      </div>
    </form>
  )
}