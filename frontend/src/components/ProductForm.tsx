import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type {
  Attribute,
  AttributeOption,
  Brand,
  Category,
  CategoryAttribute,
  ProductAttributeValueCreate,
  ProductCreateRequest,
  ProductPriceResponse,
  ProductPriceWriteRequest,
  ProductResponse,
} from '../api/productApi'

interface ProductFormProps {
  categories: Category[]
  brands: Brand[]
  attributes: Attribute[]
  options: AttributeOption[]
  categoryAttributes: CategoryAttribute[]
  submitting: boolean
  editingProduct: ProductResponse | null
  editingPrice: ProductPriceResponse | null
  onSubmit: (payload: { product: ProductCreateRequest; pricing: ProductPriceWriteRequest }) => Promise<void>
  onCancelEdit: () => void
}

type DynamicValue = string | string[]

function getInitialValues(product: ProductResponse | null): Record<number, DynamicValue> {
  if (!product) return {}
  const values: Record<number, DynamicValue> = {}
  product.attributes.forEach((item) => {
    if (item.data_type === 'MULTI_SELECT') {
      const existing = values[item.attribute_id]
      values[item.attribute_id] = [
        ...(Array.isArray(existing) ? existing : []),
        String(item.attribute_option_id),
      ]
    } else if (item.attribute_option_id !== null) {
      values[item.attribute_id] = String(item.attribute_option_id)
    } else if (item.number_value !== null) {
      values[item.attribute_id] = String(item.number_value)
    } else if (item.decimal_value !== null) {
      values[item.attribute_id] = String(item.decimal_value)
    } else {
      values[item.attribute_id] = item.text_value ?? ''
    }
  })
  return values
}

export default function ProductForm({
  categories,
  brands,
  attributes,
  options,
  categoryAttributes,
  submitting,
  editingProduct,
  editingPrice,
  onSubmit,
  onCancelEdit,
}: ProductFormProps) {
  const [categoryId, setCategoryId] = useState(() => editingProduct ? String(editingProduct.category.id) : '')
  const [brandId, setBrandId] = useState(() => editingProduct ? String(editingProduct.brand.id) : '')
  const [sku, setSku] = useState(() => editingProduct?.sku ?? '')
  const [name, setName] = useState(() => editingProduct?.name ?? '')
  const [description, setDescription] = useState(() => editingProduct?.description ?? '')
  const [salePrice, setSalePrice] = useState(() => editingPrice ? String(editingPrice.sale_price) : '')
  const [minimumSalePrice, setMinimumSalePrice] = useState(() => editingPrice?.minimum_sale_price == null ? '' : String(editingPrice.minimum_sale_price))
  const [values, setValues] = useState<Record<number, DynamicValue>>(() => getInitialValues(editingProduct))
  const [errors, setErrors] = useState<Record<string, string>>({})

  const visibleAttributes = useMemo(() => {
    const relationships = categoryAttributes
      .filter((item) => item.category_id === Number(categoryId))
      .sort((left, right) => left.display_order - right.display_order)
    return relationships
      .map((relationship) => ({
        ...relationship,
        attribute: attributes.find((item) => item.id === relationship.attribute_id),
      }))
      .filter((item): item is typeof item & { attribute: Attribute } => Boolean(item.attribute))
  }, [attributes, categoryAttributes, categoryId])

  function reset() {
    setCategoryId('')
    setBrandId('')
    setSku('')
    setName('')
    setDescription('')
    setSalePrice('')
    setMinimumSalePrice('')
    setValues({})
    setErrors({})
  }

  function handleCategoryChange(nextCategoryId: string) {
    setCategoryId(nextCategoryId)
    setValues({})
    setErrors((current) => ({ ...current, category_id: '' }))
  }

  function setValue(attributeId: number, value: DynamicValue) {
    setValues((current) => ({ ...current, [attributeId]: value }))
    setErrors((current) => ({ ...current, [`attribute_${attributeId}`]: '' }))
  }

  function validate() {
    const nextErrors: Record<string, string> = {}
    if (!categoryId) nextErrors.category_id = 'Choose a category.'
    if (!brandId) nextErrors.brand_id = 'Choose a brand.'
    if (!name.trim()) nextErrors.name = 'Product name is required.'
    if (!sku.trim()) nextErrors.sku = 'SKU is required.'
    const parsedSalePrice = Number(salePrice)
    const parsedMinimumSalePrice = minimumSalePrice === '' ? null : Number(minimumSalePrice)
    if (salePrice === '' || !Number.isFinite(parsedSalePrice) || parsedSalePrice < 0) {
      nextErrors.sale_price = 'Enter a sale price of zero or more.'
    }
    if (minimumSalePrice !== '' && (!Number.isFinite(parsedMinimumSalePrice) || parsedMinimumSalePrice! < 0)) {
      nextErrors.minimum_sale_price = 'Enter a minimum sale price of zero or more.'
    } else if (parsedMinimumSalePrice !== null && parsedMinimumSalePrice > parsedSalePrice) {
      nextErrors.minimum_sale_price = 'Minimum sale price cannot exceed sale price.'
    }

    visibleAttributes.forEach(({ attribute, is_required }) => {
      const value = values[attribute.id]
      const empty = Array.isArray(value) ? value.length === 0 : !value?.toString().trim()
      if (is_required && empty) {
        nextErrors[`attribute_${attribute.id}`] = `${attribute.name} is required.`
      }
    })
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  function buildAttributeValues(): ProductAttributeValueCreate[] {
    const payload: ProductAttributeValueCreate[] = []
    visibleAttributes.forEach(({ attribute }) => {
      const value = values[attribute.id]
      if (value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) return
      if (attribute.data_type === 'SELECT' || attribute.data_type === 'MULTI_SELECT') {
        const selected = Array.isArray(value) ? value : [value]
        selected.forEach((optionId) => payload.push({
          attribute_id: attribute.id,
          attribute_option_id: Number(optionId),
        }))
      } else if (attribute.data_type === 'NUMBER') {
        payload.push({ attribute_id: attribute.id, number_value: Number(value) })
      } else if (attribute.data_type === 'DECIMAL') {
        payload.push({ attribute_id: attribute.id, decimal_value: Number(value) })
      } else {
        payload.push({ attribute_id: attribute.id, text_value: String(value) })
      }
    })
    return payload
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!validate()) return
    await onSubmit({
      product: {
        category_id: Number(categoryId),
        brand_id: Number(brandId),
        sku: sku.trim(),
        name: name.trim(),
        description: description.trim() || undefined,
        is_active: true,
        attributes: buildAttributeValues(),
      },
      pricing: {
        sale_price: Number(salePrice),
        minimum_sale_price: minimumSalePrice === '' ? null : Number(minimumSalePrice),
      },
    })
    reset()
  }

  return (
    <form className="product-form" onSubmit={submit} noValidate>
      <div className="form-heading">
        <div>
          <p className="eyebrow">{editingProduct ? 'Edit configuration' : 'New configuration'}</p>
          <h2>{editingProduct ? 'Update product' : 'Create product'}</h2>
        </div>
        <span className="required-note"><b>*</b> Required</span>
      </div>

      <div className="form-grid form-grid--base">
        <label className={errors.category_id ? 'has-error' : ''}>
          <span>Category <b>*</b></span>
          <select value={categoryId} onChange={(event) => handleCategoryChange(event.target.value)}>
            <option value="">Select category</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          {errors.category_id && <small>{errors.category_id}</small>}
        </label>
        <label className={errors.brand_id ? 'has-error' : ''}>
          <span>Brand <b>*</b></span>
          <select value={brandId} onChange={(event) => setBrandId(event.target.value)}>
            <option value="">Select brand</option>
            {brands.map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
          </select>
          {errors.brand_id && <small>{errors.brand_id}</small>}
        </label>
        <label className={errors.name ? 'has-error' : ''}>
          <span>Product name <b>*</b></span>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. OmniBook AI 14" />
          {errors.name && <small>{errors.name}</small>}
        </label>
        <label className={errors.sku ? 'has-error' : ''}>
          <span>SKU <b>*</b></span>
          <input value={sku} onChange={(event) => setSku(event.target.value)} placeholder="e.g. HP-OMNI-14" />
          {errors.sku && <small>{errors.sku}</small>}
        </label>
      </div>

      <label className="full-width">
        <span>Description <em>Optional</em></span>
        <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} placeholder="Add a short description" />
      </label>

      <section className="attribute-section" aria-labelledby="pricing-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Selling price</p>
            <h3 id="pricing-heading">Product pricing</h3>
          </div>
        </div>
        <div className="form-grid form-grid--base">
          <label className={errors.sale_price ? 'has-error' : ''}>
            <span>Sale Price <b>*</b></span>
            <input type="number" min="0" step="0.01" value={salePrice} onChange={(event) => setSalePrice(event.target.value)} placeholder="e.g. 999.00" />
            {errors.sale_price && <small>{errors.sale_price}</small>}
          </label>
          <label className={errors.minimum_sale_price ? 'has-error' : ''}>
            <span>Minimum Sale Price <em>Optional</em></span>
            <input type="number" min="0" step="0.01" value={minimumSalePrice} onChange={(event) => setMinimumSalePrice(event.target.value)} placeholder="e.g. 899.00" />
            {errors.minimum_sale_price && <small>{errors.minimum_sale_price}</small>}
          </label>
        </div>
      </section>

      {categoryId && (
        <section className="attribute-section" aria-labelledby="attribute-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Category specification</p>
              <h3 id="attribute-heading">Product attributes</h3>
            </div>
            <span>{visibleAttributes.length} fields</span>
          </div>
          {visibleAttributes.length === 0 ? (
            <p className="empty-state">No attributes are configured for this category.</p>
          ) : (
            <div className="form-grid form-grid--attributes">
              {visibleAttributes.map(({ attribute, is_required }) => {
                const attributeOptions = options.filter((option) => option.attribute_id === attribute.id)
                const error = errors[`attribute_${attribute.id}`]
                const value = values[attribute.id] ?? (attribute.data_type === 'MULTI_SELECT' ? [] : '')
                return (
                  <label className={`attribute-field ${error ? 'has-error' : ''}`} key={attribute.id}>
                    <span>{attribute.name} {is_required && <b>*</b>} {attribute.unit && <em>({attribute.unit})</em>}</span>
                    {attribute.data_type === 'MULTI_SELECT' ? (
                      <select multiple value={Array.isArray(value) ? value : []} onChange={(event) => setValue(attribute.id, Array.from(event.target.selectedOptions, (option) => option.value))}>
                        {attributeOptions.map((option) => <option key={option.id} value={option.id}>{option.value}</option>)}
                      </select>
                    ) : attribute.data_type === 'SELECT' ? (
                      <select value={Array.isArray(value) ? '' : value} onChange={(event) => setValue(attribute.id, event.target.value)}>
                        <option value="">Select {attribute.name.toLowerCase()}</option>
                        {attributeOptions.map((option) => <option key={option.id} value={option.id}>{option.value}</option>)}
                      </select>
                    ) : (
                      <input type={attribute.data_type === 'TEXT' ? 'text' : 'number'} step={attribute.data_type === 'DECIMAL' ? 'any' : attribute.data_type === 'NUMBER' ? '1' : undefined} value={Array.isArray(value) ? '' : value} onChange={(event) => setValue(attribute.id, event.target.value)} placeholder={`Enter ${attribute.name.toLowerCase()}`} />
                    )}
                    {attribute.data_type === 'MULTI_SELECT' && <small className="field-hint">Hold Ctrl/Cmd to choose multiple</small>}
                    {error && <small>{error}</small>}
                  </label>
                )
              })}
            </div>
          )}
        </section>
      )}

      <div className="form-actions">
        {editingProduct && <button type="button" className="secondary-button" onClick={onCancelEdit} disabled={submitting}>Cancel edit</button>}
        <button type="submit" className="primary-button" disabled={submitting}>{submitting ? 'Saving...' : editingProduct ? 'Update Product' : 'Create Product'}</button>
      </div>
    </form>
  )
}