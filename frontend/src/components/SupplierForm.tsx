import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Supplier, SupplierWriteRequest } from '../api/supplierApi'

interface SupplierFormProps {
  submitting: boolean
  editingSupplier: Supplier | null
  onSubmit: (payload: SupplierWriteRequest) => Promise<void>
  onCancelEdit: () => void
}

export default function SupplierForm({
  submitting,
  editingSupplier,
  onSubmit,
  onCancelEdit,
}: SupplierFormProps) {
  const [name, setName] = useState(() => editingSupplier?.name ?? '')
  const [contactPerson, setContactPerson] = useState(() => editingSupplier?.contact_person ?? '')
  const [phone, setPhone] = useState(() => editingSupplier?.phone ?? '')
  const [email, setEmail] = useState(() => editingSupplier?.email ?? '')
  const [address, setAddress] = useState(() => editingSupplier?.address ?? '')
  const [isActive, setIsActive] = useState(() => editingSupplier?.is_active ?? true)
  const [nameError, setNameError] = useState('')

  function reset() {
    setName('')
    setContactPerson('')
    setPhone('')
    setEmail('')
    setAddress('')
    setIsActive(true)
    setNameError('')
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedName = name.trim()
    if (!trimmedName) {
      setNameError('Supplier name is required.')
      return
    }

    setNameError('')
    await onSubmit({
      name: trimmedName,
      contact_person: contactPerson.trim() || null,
      phone: phone.trim() || null,
      email: email.trim() || null,
      address: address.trim() || null,
      is_active: isActive,
    })
    if (!editingSupplier) reset()
  }

  return (
    <form className="product-form" onSubmit={submit} noValidate>
      <div className="form-heading">
        <div>
          <p className="eyebrow">{editingSupplier ? 'Supplier details' : 'New supplier'}</p>
          <h2>{editingSupplier ? 'Update supplier' : 'Add a supplier'}</h2>
        </div>
        <span className="required-note"><b>*</b> Required</span>
      </div>

      <div className="form-grid form-grid--base">
        <label className={nameError ? 'has-error' : ''}>
          <span>Supplier name <b>*</b></span>
          <input
            value={name}
            onChange={(event) => {
              setName(event.target.value)
              if (event.target.value.trim()) setNameError('')
            }}
            placeholder="e.g. Acme Components"
            aria-invalid={Boolean(nameError)}
          />
          {nameError && <small>{nameError}</small>}
        </label>
        <label>
          <span>Contact person <em>Optional</em></span>
          <input value={contactPerson} onChange={(event) => setContactPerson(event.target.value)} placeholder="e.g. Morgan Lee" />
        </label>
        <label>
          <span>Phone <em>Optional</em></span>
          <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="e.g. 555-0100" />
        </label>
        <label>
          <span>Email <em>Optional</em></span>
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="e.g. orders@example.com" />
        </label>
      </div>

      <label className="full-width">
        <span>Address <em>Optional</em></span>
        <textarea value={address} onChange={(event) => setAddress(event.target.value)} rows={3} placeholder="Supplier address" />
      </label>

      <label className="supplier-status-field">
        <span>Status</span>
        <select value={isActive ? 'active' : 'inactive'} onChange={(event) => setIsActive(event.target.value === 'active')}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>

      <div className="form-actions">
        {editingSupplier && <button type="button" className="secondary-button" onClick={onCancelEdit} disabled={submitting}>Cancel edit</button>}
        <button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Saving...' : editingSupplier ? 'Update Supplier' : 'Create Supplier'}</button>
      </div>
    </form>
  )
}