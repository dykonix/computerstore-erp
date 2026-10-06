import { useEffect, useState } from 'react'
import { createSupplier, fetchSupplier, fetchSuppliers, updateSupplier } from '../api/supplierApi'
import type { Supplier, SupplierWriteRequest } from '../api/supplierApi'
import SupplierForm from '../components/SupplierForm'
import SupplierList from '../components/SupplierList'

export default function SupplierMaster() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [listLoading, setListLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null)
  const [editingSupplierId, setEditingSupplierId] = useState<number | null>(null)

  async function loadSuppliers() {
    setListLoading(true)
    try {
      const response = await fetchSuppliers()
      setSuppliers(response.items)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load suppliers.')
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    async function load() {
      try {
        await loadSuppliers()
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load suppliers.')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  async function handleSubmit(payload: SupplierWriteRequest) {
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      if (editingSupplier) {
        await updateSupplier(editingSupplier.id, payload)
        setSuccess('Supplier updated successfully.')
        setEditingSupplier(null)
      } else {
        await createSupplier(payload)
        setSuccess('Supplier created successfully.')
      }
      await loadSuppliers()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save supplier.')
      throw submitError
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEdit(supplierId: number) {
    setError('')
    setSuccess('')
    setEditingSupplierId(supplierId)
    try {
      setEditingSupplier(await fetchSupplier(supplierId))
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load supplier.')
    } finally {
      setEditingSupplierId(null)
    }
  }

  return (
    <div className="product-page">
      <div className="page-intro">
        <div>
          <p className="eyebrow">Business directory</p>
          <h1>Supplier Master</h1>
          <p className="page-description">Keep supplier contacts and availability current for your team.</p>
        </div>
        <div className="page-mark">SM<span>03</span></div>
      </div>
      {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
      {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
      {loading ? <div className="loading-panel">Preparing your supplier workspace...</div> : <>
        <SupplierForm
          key={editingSupplier?.id ?? 'create'}
          submitting={submitting}
          editingSupplier={editingSupplier}
          onSubmit={handleSubmit}
          onCancelEdit={() => setEditingSupplier(null)}
        />
        <SupplierList suppliers={suppliers} loading={listLoading} onEdit={handleEdit} editingSupplierId={editingSupplierId} />
      </>}
    </div>
  )
}