import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Category, CategoryWriteRequest } from '../api/categoryApi'

interface CategoryFormProps {
  submitting: boolean
  editingCategory: Category | null
  onSubmit: (payload: CategoryWriteRequest) => Promise<void>
  onCancelEdit: () => void
}

export default function CategoryForm({
  submitting,
  editingCategory,
  onSubmit,
  onCancelEdit,
}: CategoryFormProps) {
  const [name, setName] = useState(() => editingCategory?.name ?? '')
  const [description, setDescription] = useState(() => editingCategory?.description ?? '')
  const [gstRate, setGstRate] = useState(() => editingCategory?.gst_rate?.toString() ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})

  function reset() {
    setName('')
    setDescription('')
    setGstRate('')
    setErrors({})
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    const trimmedName = name.trim()
    const parsedRate = gstRate.trim() === '' ? null : Number(gstRate)

    if (!trimmedName) nextErrors.name = 'Category name is required.'
    else if (trimmedName.length > 255) nextErrors.name = 'Category name must be 255 characters or fewer.'
    if (parsedRate !== null && (!Number.isFinite(parsedRate) || parsedRate < 0 || parsedRate > 100)) {
      nextErrors.gstRate = 'GST rate must be between 0 and 100.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    const payload: CategoryWriteRequest = { name: trimmedName }
    const trimmedDescription = description.trim()
    if (trimmedDescription) payload.description = trimmedDescription
    if (parsedRate !== null) payload.gst_rate = parsedRate
    await onSubmit(payload)
    if (!editingCategory) reset()
  }

  return (
    <form className="product-form" onSubmit={submit} noValidate>
      <div className="form-heading">
        <div>
          <p className="eyebrow">{editingCategory ? 'Category details' : 'New category'}</p>
          <h2>{editingCategory ? 'Update category' : 'Add a category'}</h2>
        </div>
        <span className="required-note"><b>*</b> Required</span>
      </div>

      <div className="form-grid form-grid--base category-form-grid">
        <label className={errors.name ? 'has-error' : ''}>
          <span>Category name <b>*</b></span>
          <input
            value={name}
            maxLength={255}
            onChange={(event) => {
              setName(event.target.value)
              if (event.target.value.trim()) setErrors((current) => ({ ...current, name: '' }))
            }}
            placeholder="e.g. Laptop"
            aria-invalid={Boolean(errors.name)}
          />
          {errors.name && <small>{errors.name}</small>}
        </label>
        <label className={errors.gstRate ? 'has-error' : ''}>
          <span>GST rate <em>Optional</em></span>
          <input
            type="number"
            min="0"
            max="100"
            step="0.01"
            value={gstRate}
            onChange={(event) => {
              setGstRate(event.target.value)
              setErrors((current) => ({ ...current, gstRate: '' }))
            }}
            placeholder="e.g. 18"
            aria-invalid={Boolean(errors.gstRate)}
          />
          {errors.gstRate && <small>{errors.gstRate}</small>}
        </label>
      </div>

      <label className="full-width">
        <span>Description <em>Optional</em></span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          placeholder="Add a short description"
        />
      </label>

      <div className="form-actions">
        {editingCategory && <button type="button" className="secondary-button" onClick={onCancelEdit} disabled={submitting}>Cancel edit</button>}
        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? 'Saving...' : editingCategory ? 'Update Category' : 'Create Category'}
        </button>
      </div>
    </form>
  )
}