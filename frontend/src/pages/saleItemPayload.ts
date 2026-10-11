import type { PromotionSaleGroup } from '../api/promotionApi'
import type { AddSaleItemRequest, SaleItemResponse } from '../api/salesApi'

export type FulfillmentSource = 'STORE' | 'MANUFACTURER'

export interface SaleItemPayloadInput {
  productId: number
  quantity: number
  actualUnitPrice: number
  minimumPrice: number | null
  minimumPriceOverride: boolean
  isFreeProduct: boolean
  promotionId: number | null
  benefitGroups: PromotionSaleGroup[]
  benefitIdsByUnit: number[][]
  sourcesByUnit: Array<Record<number, FulfillmentSource>>
}

export function buildSaleItemPayload(input: SaleItemPayloadInput): AddSaleItemRequest {
  const payload: AddSaleItemRequest = {
    product_id: input.productId,
    quantity: input.quantity,
    actual_unit_price: input.isFreeProduct ? 0 : input.actualUnitPrice,
    configured_minimum_price: input.minimumPrice ?? 0,
    minimum_price_override: input.minimumPriceOverride,
    is_free_product: input.isFreeProduct,
    promotion_id: input.promotionId,
  }

  // Without a promotion there are no benefit selections and therefore no sources to send.
  if (input.promotionId === null) return payload

  const productBenefitIds = new Set(
    input.benefitGroups
      .flatMap((group) => group.benefits)
      .filter((benefit) => benefit.benefit_type === 'PRODUCT')
      .map((benefit) => benefit.id),
  )
  const idsByUnit = Array.from({ length: input.quantity }, (_, unit) => input.benefitIdsByUnit[unit] ?? [])

  payload.promotion_benefit_ids_by_unit = idsByUnit
  // A source is sent only for a product benefit that is selected for that unit.
  payload.promotion_benefit_sources_by_unit = idsByUnit.map((benefitIds, unit) =>
    Object.fromEntries(
      benefitIds
        .filter((id) => productBenefitIds.has(id))
        .map((id) => [id, input.sourcesByUnit[unit]?.[id] ?? 'MANUFACTURER']),
    ),
  )
  return payload
}

// Benefit lines are separate sale lines; only a qualifying product line counts as "already added".
export function isProductInCart(items: SaleItemResponse[], productId: number): boolean {
  return items.some((item) => !item.is_promotion_benefit && item.product_id === productId)
}
