import { useEffect, useState } from 'react'
import { fetchProducts } from '../api/productApi'
import type { ProductListItem } from '../api/productApi'
import {
  createWarrantyOption,
  createWarrantyPrice,
  fetchWarrantyOption,
  fetchWarrantyOptions,
  fetchWarrantyPrices,
  setWarrantyOptionStatus,
  updateWarrantyOption,
  updateWarrantyPrice,
} from '../api/warrantyApi'
import type {
  WarrantyOption,
  WarrantyPrice,
  WarrantyPriceWriteRequest,
} from '../api/warrantyApi'
import WarrantyForm from '../components/WarrantyForm'
import type { WarrantyOptionFormData } from '../components/WarrantyForm'
import WarrantyList from '../components/WarrantyList'
import WarrantyPriceForm from '../components/WarrantyPriceForm'
import WarrantyPriceList from '../components/WarrantyPriceList'

export default function WarrantyMaster() {
  const [products, setProducts] = useState<ProductListItem[]>([])
  const [selectedProductId, setSelectedProductId] = useState('')
  const [options, setOptions] = useState<WarrantyOption[]>([])
  const [selectedOption, setSelectedOption] = useState<WarrantyOption | null>(null)
  const [prices, setPrices] = useState<WarrantyPrice[]>([])
  const [editingOption, setEditingOption] = useState<WarrantyOption | null>(null)
  const [editingPrice, setEditingPrice] = useState<WarrantyPrice | null>(null)
  const [loading, setLoading] = useState(true)
  const [optionsLoading, setOptionsLoading] = useState(false)
  const [pricesLoading, setPricesLoading] = useState(false)
  const [submittingOption, setSubmittingOption] = useState(false)
  const [submittingPrice, setSubmittingPrice] = useState(false)
  const [editingOptionId, setEditingOptionId] = useState<number | null>(null)
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function loadOptions(productId: number) {
    setOptionsLoading(true)
    try {
      const nextOptions = await fetchWarrantyOptions(productId)
      setOptions(nextOptions)
      if (selectedOption && !nextOptions.some((option) => option.id === selectedOption.id)) {
        setSelectedOption(null)
        setPrices([])
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load warranty options.')
    } finally {
      setOptionsLoading(false)
    }
  }

  async function loadPrices(optionId: number) {
    setPricesLoading(true)
    try {
      setPrices(await fetchWarrantyPrices(optionId))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load warranty prices.')
    } finally {
      setPricesLoading(false)
    }
  }

  useEffect(() => {
    async function loadProducts() {
      try {
        const response = await fetchProducts()
        setProducts(response.items)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unable to load products.')
      } finally {
        setLoading(false)
      }
    }
    void loadProducts()
  }, [])

  useEffect(() => {
    if (!selectedProductId) return
    let cancelled = false
    async function loadSelectedProductOptions() {
      try {
        const nextOptions = await fetchWarrantyOptions(Number(selectedProductId))
        if (!cancelled) setOptions(nextOptions)
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : 'Unable to load warranty options.')
      } finally {
        if (!cancelled) setOptionsLoading(false)
      }
    }
    void loadSelectedProductOptions()
    return () => { cancelled = true }
  }, [selectedProductId])

  function handleProductChange(productId: string) {
    setSelectedProductId(productId)
    setOptions([])
    setSelectedOption(null)
    setPrices([])
    setEditingOption(null)
    setEditingPrice(null)
    setOptionsLoading(Boolean(productId))
  }

  async function handleOptionSubmit(payload: WarrantyOptionFormData) {
    setSubmittingOption(true)
    setError('')
    setSuccess('')
    try {
      let savedOption: WarrantyOption
      if (editingOption) {
        savedOption = await updateWarrantyOption(editingOption.id, {
          additional_months: payload.additional_months,
        })
        if (editingOption.is_active !== payload.is_active) {
          savedOption = await setWarrantyOptionStatus(savedOption.id, payload.is_active)
        }
        setSuccess('Warranty option updated successfully.')
        setEditingOption(null)
      } else {
        savedOption = await createWarrantyOption({
          product_id: payload.product_id,
          additional_months: payload.additional_months,
        })
        if (!payload.is_active) {
          savedOption = await setWarrantyOptionStatus(savedOption.id, false)
        }
        setSelectedProductId(payload.product_id.toString())
        setSuccess('Warranty option created successfully.')
      }
      await loadOptions(savedOption.product_id)
      setSelectedOption(savedOption)
      await loadPrices(savedOption.id)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save warranty option.')
      throw submitError
    } finally {
      setSubmittingOption(false)
    }
  }

  async function handleEditOption(optionId: number) {
    setEditingOptionId(optionId)
    setError('')
    setSuccess('')
    try {
      const option = await fetchWarrantyOption(optionId)
      setSelectedProductId(option.product_id.toString())
      setSelectedOption(option)
      setEditingOption(option)
      await loadPrices(option.id)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load warranty option.')
    } finally {
      setEditingOptionId(null)
    }
  }

  async function handleToggleOptionStatus(option: WarrantyOption) {
    setStatusUpdatingId(option.id)
    setError('')
    setSuccess('')
    try {
      const updated = await setWarrantyOptionStatus(option.id, !option.is_active)
      setSuccess(`Warranty option ${updated.is_active ? 'activated' : 'deactivated'} successfully.`)
      if (selectedOption?.id === option.id) setSelectedOption(updated)
      await loadOptions(option.product_id)
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : 'Unable to update warranty option status.')
    } finally {
      setStatusUpdatingId(null)
    }
  }

  async function handlePriceSubmit(payload: WarrantyPriceWriteRequest) {
    if (!selectedOption) return
    setSubmittingPrice(true)
    setError('')
    setSuccess('')
    try {
      if (editingPrice) {
        await updateWarrantyPrice(editingPrice.id, payload)
        setSuccess('Warranty price updated successfully.')
        setEditingPrice(null)
      } else {
        await createWarrantyPrice(selectedOption.id, payload)
        setSuccess('Warranty price created successfully.')
      }
      await loadPrices(selectedOption.id)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save warranty price.')
      throw submitError
    } finally {
      setSubmittingPrice(false)
    }
  }

  async function handleEditPrice(priceId: number) {
    const price = prices.find((item) => item.id === priceId)
    if (price) setEditingPrice(price)
  }

  return (
    <div className="product-page">
      <div className="page-intro">
        <div>
          <p className="eyebrow">Product services</p>
          <h1>Warranty Management</h1>
          <p className="page-description">Manage additional coverage options and their price periods.</p>
        </div>
        <div className="page-mark">WM<span>05</span></div>
      </div>
      {error && <div className="notice notice--error" role="alert"><strong>Something needs attention</strong><span>{error}</span></div>}
      {success && <div className="notice notice--success" role="status"><strong>Saved</strong><span>{success}</span></div>}
      {loading ? <div className="loading-panel">Preparing your warranty workspace...</div> : <>
        {products.length === 0 && <div className="empty-state">No products are available for warranty setup.</div>}
        <WarrantyForm
          key={editingOption?.id ?? 'create'}
          products={products}
          selectedProductId={selectedProductId}
          submitting={submittingOption}
          editingOption={editingOption}
          onProductChange={handleProductChange}
          onSubmit={handleOptionSubmit}
          onCancelEdit={() => setEditingOption(null)}
        />
        {selectedProductId && <WarrantyList
          options={options}
          loading={optionsLoading}
          selectedOptionId={selectedOption?.id ?? null}
          editingOptionId={editingOptionId}
          statusUpdatingId={statusUpdatingId}
          onSelectPrices={(option) => { setSelectedOption(option); setEditingPrice(null); void loadPrices(option.id) }}
          onEdit={handleEditOption}
          onToggleStatus={handleToggleOptionStatus}
        />}
        {selectedOption && <section className="warranty-pricing-section">
          <div className="section-heading warranty-pricing-heading">
            <div>
              <p className="eyebrow">{selectedOption.additional_months} months additional coverage</p>
              <h2>Pricing</h2>
            </div>
            <span>{selectedOption.is_active ? 'Active option' : 'Inactive option'}</span>
          </div>
          <WarrantyPriceForm
            key={editingPrice?.id ?? `price-${selectedOption.id}`}
            submitting={submittingPrice}
            editingPrice={editingPrice}
            onSubmit={handlePriceSubmit}
            onCancelEdit={() => setEditingPrice(null)}
          />
          <WarrantyPriceList prices={prices} loading={pricesLoading} onEdit={handleEditPrice} />
        </section>}
      </>}
    </div>
  )
}