import assert from 'node:assert/strict'
import { test } from 'node:test'

import { buildSaleItemPayload, isProductInCart } from '../src/pages/saleItemPayload.ts'

const group = (id, benefits) => ({
  id,
  promotion_id: 1,
  name: `Group ${id}`,
  selection_rule: 'OPTIONAL',
  group_requirement: 'OPTIONAL',
  benefit_selection_rule: 'ANY',
  benefits,
})
const productBenefit = (id) => ({ id, benefit_type: 'PRODUCT', product_id: id + 100 })
const cashbackBenefit = (id) => ({ id, benefit_type: 'CASHBACK', product_id: null })

const base = {
  productId: 5,
  quantity: 2,
  actualUnitPrice: 1000,
  minimumPrice: 900,
  minimumPriceOverride: false,
  isFreeProduct: false,
  promotionId: null,
  benefitGroups: [],
  benefitIdsByUnit: [],
  sourcesByUnit: [],
}

test('a product without a promotion sends no benefit selections or sources', () => {
  const payload = buildSaleItemPayload({
    ...base,
    // Stale state from a previously chosen promotion must not leak into the request.
    benefitGroups: [group(1, [productBenefit(10)])],
    benefitIdsByUnit: [[10], [10]],
    sourcesByUnit: [{ 10: 'STORE' }, { 10: 'STORE' }],
  })

  assert.equal(payload.promotion_id, null)
  assert.equal('promotion_benefit_ids_by_unit' in payload, false)
  assert.equal('promotion_benefit_sources_by_unit' in payload, false)
  assert.equal(payload.quantity, 2)
})

test('each unit sends its own selection and a source only for selected product benefits', () => {
  const payload = buildSaleItemPayload({
    ...base,
    promotionId: 1,
    benefitGroups: [group(1, [productBenefit(10), productBenefit(11), productBenefit(12), cashbackBenefit(13)])],
    benefitIdsByUnit: [[10, 13], [11]],
    // 12 is unselected but has a stale source; 13 is cashback and never takes a source.
    sourcesByUnit: [{ 10: 'STORE', 12: 'STORE', 13: 'STORE' }, {}],
  })

  assert.deepEqual(payload.promotion_benefit_ids_by_unit, [[10, 13], [11]])
  assert.deepEqual(payload.promotion_benefit_sources_by_unit, [{ 10: 'STORE' }, { 11: 'MANUFACTURER' }])
})

test('units without a selection send an empty selection and no sources', () => {
  const payload = buildSaleItemPayload({
    ...base,
    promotionId: 1,
    benefitGroups: [group(1, [productBenefit(10)])],
    benefitIdsByUnit: [[10]],
    sourcesByUnit: [{ 10: 'STORE' }],
  })

  assert.deepEqual(payload.promotion_benefit_ids_by_unit, [[10], []])
  assert.deepEqual(payload.promotion_benefit_sources_by_unit, [{ 10: 'STORE' }, {}])
})

test('a free product is priced at zero', () => {
  assert.equal(buildSaleItemPayload({ ...base, isFreeProduct: true }).actual_unit_price, 0)
})

test('only a qualifying product line counts as already in the cart', () => {
  const line = (product_id, is_promotion_benefit) => ({ product_id, is_promotion_benefit })
  const items = [line(5, false), line(6, true)]

  assert.equal(isProductInCart(items, 5), true)
  assert.equal(isProductInCart(items, 6), false)
  assert.equal(isProductInCart([], 5), false)
})
