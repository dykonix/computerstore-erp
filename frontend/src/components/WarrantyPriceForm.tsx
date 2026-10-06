import { useState } from 'react'
import type { FormEvent } from 'react'
import type { WarrantyPrice, WarrantyPriceWriteRequest } from '../api/warrantyApi'

interface WarrantyPriceFormProps {
  submitting: boolean
  editingPrice: WarrantyPrice | null
  onSubmit: (payload: WarrantyPriceWriteRequest) => Promise<void>
  onCancelEdit: () => void
}

export default function WarrantyPriceForm({
  submitting,
  editingPrice,
  onSubmit,
  onCancelEdit,
}: WarrantyPriceFormProps) {
  const [price, setPrice] = useState(() => editingPrice?.price.toString() ?? '')
  const [validFrom, setValidFrom] = useState(() => editingPrice?.valid_from ?? '')
  const [validTo, setValidTo] = useState(() => editingPrice?.valid_to ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})

  function reset() {
    setPrice('')
    setValidFrom('')
    setValidTo('')
    setErrors({})
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const numericPrice = Number(price)
    const nextErrors: Record<string, string> = {}
    if (price.trim() === '' || !Number.isFinite(numericPrice) || numericPrice < 0) {
      nextErrors.price = 'Price must be zero or greater.'
    }
    if (!validFrom) nextErrors.validFrom = 'Valid from date is required.'
    if (validTo && validFrom && validTo < validFrom) {
      nextErrors.validTo = 'Valid to cannot be earlier than valid from.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    await onSubmit({
      price: numericPrice,
      valid_from: validFrom,
      valid_to: validTo || null,
    })
    if (!editingPrice) reset()
  }

  return (
    <form className="product-form warranty-price-form" onSubmit={submit} noValidate>
      <div className="form-heading">
        <div>
          <p className="eyebrow">Warranty pricing</p>
          <h3>{editingPrice ? 'Update price period' : 'Add a price period'}</h3>
        </div>
        <span className="required-note"><b>*</b> Required</span>
      </div>
      <div className="form-grid form-grid--base warranty-price-grid">
        <label className={errors.price ? 'has-error' : ''}>
          <span>Price <b>*</b></span>
          <input type="number" min="0" step="0.01" value={price} onChange={(event) => { setPrice(event.target.value); setErrors((current) => ({ ...current, price: '' })) }} placeholder="e.g. 1499.00" />
          {errors.price && <small>{errors.price}</small>}
        </label>
        <label className={errors.validFrom ? 'has-error' : ''}>
          <span>Valid from <b>*</b></span>
          <input type="date" value={validFrom} onChange={(event) => { setValidFrom(event.target.value); setErrors((current) => ({ ...current, validFrom: '', validTo: '' })) }} />
          {errors.validFrom && <small>{errors.validFrom}</small>}
        </label>
        <label className={errors.validTo ? 'has-error' : ''}>
          <span>Valid to <em>Optional</em></span>
          <input type="date" value={validTo} onChange={(event) => { setValidTo(event.target.value); setErrors((current) => ({ ...current, validTo: '' })) }} />
          {errors.validTo && <small>{errors.validTo}</small>}
        </label>
      </div>
      <div className="form-actions">
        {editingPrice && <button type="button" className="secondary-button" onClick={onCancelEdit} disabled={submitting}>Cancel edit</button>}
        <button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Saving...' : editingPrice ? 'Update Price' : 'Add Price'}</button>
      </div>
    </form>
  )
}