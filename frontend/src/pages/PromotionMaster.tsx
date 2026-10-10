import { useEffect, useMemo, useState } from 'react'
import {
  createCashbackBenefit,
  createProductBenefit,
  createPromotion,
  createPromotionGroup,
  createWarrantyBenefit,
  deletePromotionGroup,
  fetchPromotionBenefits,
  fetchPromotionGroups,
  fetchPromotionProducts,
  fetchPromotions,
  replacePromotionProducts,
  updatePromotion,
  type Promotion,
  type PromotionBenefit,
  type PromotionGroup,
} from '../api/promotionApi'
import { fetchProducts } from '../api/productApi'
import type { ProductListItem } from '../api/productApi'

type BenefitFormType = 'PRODUCT' | 'WARRANTY' | 'CASHBACK'

const selectionRules = ['REQUIRED', 'ONE', 'ALL', 'OPTIONAL'] as const

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString()
}

function formatBenefit(
  benefit: PromotionBenefit,
  products: ProductListItem[],
): string {
  if (benefit.benefit_type === 'PRODUCT') {
    const product = products.find((item) => item.id === benefit.product_id)
    return `Product: ${product?.name ?? `Product #${benefit.product_id}`} — ₹${Number(
      benefit.promotion_price ?? 0,
    ).toFixed(2)}`
  }

  if (benefit.benefit_type === 'WARRANTY') {
    return `Warranty #${benefit.warranty_option_id} — ₹${Number(
      benefit.promotion_price ?? 0,
    ).toFixed(2)}`
  }

  return `Cashback: ₹${Number(
    benefit.cashback_amount ?? 0,
  ).toFixed(2)} via ${benefit.payment_mode}`
}

export default function PromotionMaster() {
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [products, setProducts] = useState<ProductListItem[]>([])

  const [selectedPromotion, setSelectedPromotion] =
    useState<Promotion | null>(null)

  const [qualifyingProductIds, setQualifyingProductIds] = useState<number[]>(
    [],
  )

  const [groups, setGroups] = useState<PromotionGroup[]>([])
  const [benefits, setBenefits] = useState<Record<number, PromotionBenefit[]>>(
    {},
  )

  const [editingPromotionId, setEditingPromotionId] = useState<number | null>(
    null,
  )

  const [name, setName] = useState('')
  const [validFrom, setValidFrom] = useState('')
  const [validTo, setValidTo] = useState('')
  const [isActive, setIsActive] = useState(true)

  const [groupName, setGroupName] = useState('')
  const [groupRule, setGroupRule] =
    useState<(typeof selectionRules)[number]>('REQUIRED')

  const [benefitGroupId, setBenefitGroupId] = useState<number | null>(null)
  const [benefitType, setBenefitType] =
    useState<BenefitFormType>('PRODUCT')

  const [benefitProductId, setBenefitProductId] = useState('')
  const [benefitWarrantyId, setBenefitWarrantyId] = useState('')
  const [benefitPrice, setBenefitPrice] = useState('')
  const [cashbackAmount, setCashbackAmount] = useState('')
  const [cashbackPaymentMode, setCashbackPaymentMode] = useState('UPI')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const activeProducts = useMemo(
    () => products.filter((product) => product.is_active),
    [products],
  )

  async function loadPromotions() {
    const response = await fetchPromotions()
    setPromotions(response)
  }

  async function loadPromotionDetails(promotion: Promotion) {
    const [productRows, groupRows] = await Promise.all([
      fetchPromotionProducts(promotion.id),
      fetchPromotionGroups(promotion.id),
    ])

    setSelectedPromotion(promotion)
    setQualifyingProductIds(productRows.map((item) => item.product_id))
    setGroups(groupRows)

    const benefitEntries = await Promise.all(
      groupRows.map(async (group) => {
        const rows = await fetchPromotionBenefits(group.id)
        return [group.id, rows] as const
      }),
    )

    setBenefits(Object.fromEntries(benefitEntries))
  }

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')

      try {
        const [promotionRows, productResponse] = await Promise.all([
          fetchPromotions(),
          fetchProducts(),
        ])

        setPromotions(promotionRows)
        setProducts(productResponse.items)

        if (promotionRows.length > 0) {
          await loadPromotionDetails(promotionRows[0])
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Unable to load promotions.',
        )
      } finally {
        setLoading(false)
      }
    }

    void load()
  }, [])

  function resetPromotionForm() {
    setEditingPromotionId(null)
    setName('')
    setValidFrom('')
    setValidTo('')
    setIsActive(true)
  }

  function startCreatePromotion() {
    setSelectedPromotion(null)
    setQualifyingProductIds([])
    setGroups([])
    setBenefits({})
    resetPromotionForm()
    setSuccess('')
    setError('')
  }

  function startEditPromotion(promotion: Promotion) {
    setEditingPromotionId(promotion.id)
    setName(promotion.name)
    setValidFrom(promotion.valid_from)
    setValidTo(promotion.valid_to)
    setIsActive(promotion.is_active)
    setSuccess('')
    setError('')
  }

  async function handlePromotionSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setSaving(true)
    setError('')
    setSuccess('')

    try {
      const payload = {
        name,
        valid_from: validFrom,
        valid_to: validTo,
        is_active: isActive,
      }

      if (editingPromotionId !== null) {
        const updated = await updatePromotion(
          editingPromotionId,
          payload,
        )

        await loadPromotions()
        await loadPromotionDetails(updated)

        setSuccess('Promotion updated successfully.')
      } else {
        const created = await createPromotion(payload)

        await loadPromotions()
        await loadPromotionDetails(created)

        setSuccess('Promotion created successfully.')
      }

      setEditingPromotionId(null)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'Unable to save promotion.',
      )
    } finally {
      setSaving(false)
    }
  }

  async function toggleQualifyingProduct(productId: number) {
    if (!selectedPromotion) {
      return
    }

    const nextIds = qualifyingProductIds.includes(productId)
      ? qualifyingProductIds.filter((id) => id !== productId)
      : [...qualifyingProductIds, productId]

    setError('')

    try {
      await replacePromotionProducts(selectedPromotion.id, nextIds)
      setQualifyingProductIds(nextIds)
      setSuccess('Qualifying products updated.')
    } catch (toggleError) {
      setError(
        toggleError instanceof Error
          ? toggleError.message
          : 'Unable to update qualifying products.',
      )
    }
  }

  async function handleCreateGroup(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!selectedPromotion) {
      return
    }

    if (!groupName.trim()) {
      setError('Group name is required.')
      return
    }

    try {
      setError('')

      const group = await createPromotionGroup(selectedPromotion.id, {
        name: groupName.trim(),
        selection_rule: groupRule,
      })

      setGroups((current) => [...current, group])
      setBenefits((current) => ({
        ...current,
        [group.id]: [],
      }))

      setGroupName('')
      setGroupRule('REQUIRED')
      setSuccess('Benefit group created.')
    } catch (groupError) {
      setError(
        groupError instanceof Error
          ? groupError.message
          : 'Unable to create benefit group.',
      )
    }
  }

  async function handleDeleteGroup(groupId: number) {
    try {
      setError('')
      await deletePromotionGroup(groupId)

      setGroups((current) =>
        current.filter((group) => group.id !== groupId),
      )

      setBenefits((current) => {
        const next = { ...current }
        delete next[groupId]
        return next
      })

      if (benefitGroupId === groupId) {
        setBenefitGroupId(null)
      }

      setSuccess('Benefit group deleted.')
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete benefit group.',
      )
    }
  }

  async function handleCreateBenefit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!benefitGroupId) {
      setError('Select a benefit group first.')
      return
    }

    try {
      setError('')

      let benefit: PromotionBenefit

      if (benefitType === 'PRODUCT') {
        const productId = Number(benefitProductId)
        const price = Number(benefitPrice)

        if (!productId || Number.isNaN(price) || price < 0) {
          setError('Select a product and enter a valid promotion price.')
          return
        }

        benefit = await createProductBenefit(benefitGroupId, {
          product_id: productId,
          promotion_price: price,
        })
      } else if (benefitType === 'WARRANTY') {
        const warrantyId = Number(benefitWarrantyId)
        const price = Number(benefitPrice)

        if (!warrantyId || Number.isNaN(price) || price < 0) {
          setError(
            'Enter a valid warranty option ID and promotion price.',
          )
          return
        }

        benefit = await createWarrantyBenefit(benefitGroupId, {
          warranty_option_id: warrantyId,
          promotion_price: price,
        })
      } else {
        const amount = Number(cashbackAmount)

        if (Number.isNaN(amount) || amount < 0) {
          setError('Enter a valid cashback amount.')
          return
        }

        benefit = await createCashbackBenefit(benefitGroupId, {
          cashback_amount: amount,
          payment_mode: cashbackPaymentMode,
        })
      }

      setBenefits((current) => ({
        ...current,
        [benefitGroupId]: [
          ...(current[benefitGroupId] ?? []),
          benefit,
        ],
      }))

      setBenefitProductId('')
      setBenefitWarrantyId('')
      setBenefitPrice('')
      setCashbackAmount('')
      setSuccess('Benefit added.')
    } catch (benefitError) {
      setError(
        benefitError instanceof Error
          ? benefitError.message
          : 'Unable to create benefit.',
      )
    }
  }

  if (loading) {
    return (
      <div className="loading-panel">
        Preparing promotion workspace...
      </div>
    )
  }

  return (
    <div>
      <div className="page-intro">
        <div>
          <p className="eyebrow">Commercial management</p>
          <h1>Promotions</h1>
          <p className="page-description">
            Configure V1 product promotions, qualifying products and
            customer benefits.
          </p>
        </div>

        <div className="page-mark">
          PR<span>01</span>
        </div>
      </div>

      {error && (
        <div className="notice notice--error" role="alert">
          <strong>Something needs attention</strong>
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="notice notice--success" role="status">
          <strong>Saved</strong>
          <span>{success}</span>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(260px, 320px) 1fr',
          gap: '24px',
          alignItems: 'start',
        }}
      >
        <section
          style={{
            border: '1px solid #e5e5e5',
            borderRadius: '8px',
            padding: '20px',
            background: '#fff',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px',
            }}
          >
            <h2 style={{ margin: 0 }}>Promotions</h2>
            <button type="button" onClick={startCreatePromotion}>
              New
            </button>
          </div>

          {promotions.length === 0 ? (
            <p>No promotions created yet.</p>
          ) : (
            <div style={{ display: 'grid', gap: '8px' }}>
              {promotions.map((promotion) => (
                <button
                  key={promotion.id}
                  type="button"
                  onClick={() => {
                    void loadPromotionDetails(promotion)
                  }}
                  style={{
                    textAlign: 'left',
                    padding: '12px',
                    border: '1px solid #ddd',
                    borderRadius: '6px',
                    background:
                      selectedPromotion?.id === promotion.id
                        ? '#f5f5f5'
                        : '#fff',
                  }}
                >
                  <strong>{promotion.name}</strong>
                  <br />
                  <small>
                    {formatDate(promotion.valid_from)} –{' '}
                    {formatDate(promotion.valid_to)}
                  </small>
                  <br />
                  <small>
                    {promotion.is_active ? 'Active' : 'Inactive'}
                  </small>
                </button>
              ))}
            </div>
          )}
        </section>

        <section
          style={{
            border: '1px solid #e5e5e5',
            borderRadius: '8px',
            padding: '20px',
            background: '#fff',
          }}
        >
          <form onSubmit={handlePromotionSubmit}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h2>
                {editingPromotionId
                  ? 'Edit Promotion'
                  : selectedPromotion
                    ? selectedPromotion.name
                    : 'New Promotion'}
              </h2>

              {selectedPromotion && !editingPromotionId && (
                <button
                  type="button"
                  onClick={() => startEditPromotion(selectedPromotion)}
                >
                  Edit
                </button>
              )}
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr 1fr',
                gap: '12px',
                marginBottom: '16px',
              }}
            >
              <label>
                Promotion name
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Festival Offer"
                  required
                />
              </label>

              <label>
                Valid from
                <input
                  type="date"
                  value={validFrom}
                  onChange={(event) => setValidFrom(event.target.value)}
                  required
                />
              </label>

              <label>
                Valid to
                <input
                  type="date"
                  value={validTo}
                  onChange={(event) => setValidTo(event.target.value)}
                  required
                />
              </label>
            </div>

            <label
              style={{
                display: 'flex',
                gap: '8px',
                alignItems: 'center',
                marginBottom: '16px',
              }}
            >
              <input
                type="checkbox"
                checked={isActive}
                onChange={(event) => setIsActive(event.target.checked)}
              />
              Active
            </label>

            {(editingPromotionId !== null || !selectedPromotion) && (
              <button type="submit" disabled={saving}>
                {saving
                  ? 'Saving...'
                  : editingPromotionId
                    ? 'Update Promotion'
                    : 'Create Promotion'}
              </button>
            )}
          </form>

          {selectedPromotion && (
            <>
              <hr style={{ margin: '28px 0' }} />

              <h2>Qualifying Products</h2>

              <p>
                Select the products for which this promotion is
                applicable.
              </p>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns:
                    'repeat(auto-fill, minmax(240px, 1fr))',
                  gap: '8px',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  border: '1px solid #eee',
                  padding: '12px',
                }}
              >
                {activeProducts.map((product) => {
                  const selected = qualifyingProductIds.includes(
                    product.id,
                  )

                  return (
                    <label
                      key={product.id}
                      style={{
                        display: 'flex',
                        gap: '8px',
                        alignItems: 'flex-start',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => {
                          void toggleQualifyingProduct(product.id)
                        }}
                      />

                      <span>
                        <strong>{product.name}</strong>
                        <br />
                        <small>
                          {product.brand.name} · {product.sku}
                        </small>
                      </span>
                    </label>
                  )
                })}
              </div>

              <hr style={{ margin: '28px 0' }} />

              <h2>Benefit Groups</h2>

              <form
                onSubmit={handleCreateGroup}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr auto',
                  gap: '10px',
                  marginBottom: '20px',
                }}
              >
                <input
                  value={groupName}
                  onChange={(event) => setGroupName(event.target.value)}
                  placeholder="Student Benefit"
                />

                <select
                  value={groupRule}
                  onChange={(event) =>
                    setGroupRule(
                      event.target.value as (typeof selectionRules)[number],
                    )
                  }
                >
                  {selectionRules.map((rule) => (
                    <option key={rule} value={rule}>
                      {rule}
                    </option>
                  ))}
                </select>

                <button type="submit">Add Group</button>
              </form>

              {groups.length === 0 ? (
                <p>No benefit groups configured.</p>
              ) : (
                <div style={{ display: 'grid', gap: '16px' }}>
                  {groups.map((group) => {
                    const groupBenefits = benefits[group.id] ?? []

                    return (
                      <div
                        key={group.id}
                        style={{
                          border: '1px solid #ddd',
                          borderRadius: '8px',
                          padding: '16px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: '12px',
                          }}
                        >
                          <div>
                            <strong>{group.name}</strong>
                            <div>
                              <small>
                                Selection rule: {group.selection_rule}
                              </small>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              void handleDeleteGroup(group.id)
                            }}
                          >
                            Delete
                          </button>
                        </div>

                        <div style={{ marginTop: '12px' }}>
                          <strong>Benefits</strong>

                          {groupBenefits.length === 0 ? (
                            <p>No benefits yet.</p>
                          ) : (
                            <ul>
                              {groupBenefits.map((benefit) => (
                                <li key={benefit.id}>
                                  {formatBenefit(benefit, products)}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        <div
                          style={{
                            marginTop: '16px',
                            paddingTop: '16px',
                            borderTop: '1px solid #eee',
                          }}
                        >
                          <h3 style={{ marginTop: 0 }}>
                            Add Benefit
                          </h3>

                          <form
                            onSubmit={handleCreateBenefit}
                            style={{
                              display: 'grid',
                              gap: '10px',
                            }}
                          >
                            <select
                              value={
                                benefitGroupId === group.id
                                  ? benefitType
                                  : ''
                              }
                              onChange={(event) => {
                                setBenefitGroupId(group.id)
                                setBenefitType(
                                  event.target.value as BenefitFormType,
                                )
                              }}
                            >
                              <option value="" disabled>
                                Select benefit type
                              </option>
                              <option value="PRODUCT">
                                Product
                              </option>
                              <option value="WARRANTY">
                                Warranty
                              </option>
                              <option value="CASHBACK">
                                Cashback
                              </option>
                            </select>

                            {benefitGroupId === group.id &&
                              benefitType === 'PRODUCT' && (
                                <>
                                  <select
                                    value={benefitProductId}
                                    onChange={(event) =>
                                      setBenefitProductId(
                                        event.target.value,
                                      )
                                    }
                                  >
                                    <option value="">
                                      Select product
                                    </option>

                                    {activeProducts.map((product) => (
                                      <option
                                        key={product.id}
                                        value={product.id}
                                      >
                                        {product.name} — {product.sku}
                                      </option>
                                    ))}
                                  </select>

                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={benefitPrice}
                                    onChange={(event) =>
                                      setBenefitPrice(event.target.value)
                                    }
                                    placeholder="Promotion price"
                                  />
                                </>
                              )}

                            {benefitGroupId === group.id &&
                              benefitType === 'WARRANTY' && (
                                <>
                                  <input
                                    type="number"
                                    min="1"
                                    value={benefitWarrantyId}
                                    onChange={(event) =>
                                      setBenefitWarrantyId(
                                        event.target.value,
                                      )
                                    }
                                    placeholder="Warranty option ID"
                                  />

                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={benefitPrice}
                                    onChange={(event) =>
                                      setBenefitPrice(event.target.value)
                                    }
                                    placeholder="Promotion price"
                                  />

                                  <small>
                                    Enter the warranty option ID from
                                    Warranty Master.
                                  </small>
                                </>
                              )}

                            {benefitGroupId === group.id &&
                              benefitType === 'CASHBACK' && (
                                <>
                                  <input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={cashbackAmount}
                                    onChange={(event) =>
                                      setCashbackAmount(
                                        event.target.value,
                                      )
                                    }
                                    placeholder="Cashback amount"
                                  />

                                  <select
                                    value={cashbackPaymentMode}
                                    onChange={(event) =>
                                      setCashbackPaymentMode(
                                        event.target.value,
                                      )
                                    }
                                  >
                                    <option value="UPI">UPI</option>
                                  </select>
                                </>
                              )}

                            {benefitGroupId === group.id && (
                              <button type="submit">
                                Add Benefit
                              </button>
                            )}
                          </form>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  )
}