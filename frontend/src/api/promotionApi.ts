import { apiRequest } from './apiClient'

export interface Promotion {
  id: number
  tenant_id: number
  name: string
  valid_from: string
  valid_to: string
  is_active: boolean
}

export interface ProductPromotion {
  id: number
  name: string
  cashback_amount: number
}

export interface PromotionCreateRequest {
  name: string
  valid_from: string
  valid_to: string
  is_active: boolean
}

export interface PromotionProduct {
  product_id: number
}

export interface PromotionProductsRequest {
  product_ids: number[]
}

export interface PromotionGroup {
  id: number
  promotion_id: number
  name: string
  selection_rule: string
}

export interface PromotionGroupRequest {
  name: string
  selection_rule: string
}

export interface PromotionBenefit {
  id: number
  promotion_group_id: number
  benefit_type: 'PRODUCT' | 'WARRANTY' | 'CASHBACK'
  product_id: number | null
  warranty_option_id: number | null
  promotion_price: number | null
  cashback_amount: number | null
  payment_mode: string | null
}

export interface ProductBenefitRequest {
  product_id: number
  promotion_price: number
}

export interface WarrantyBenefitRequest {
  warranty_option_id: number
  promotion_price: number
}

export interface CashbackBenefitRequest {
  cashback_amount: number
  payment_mode: string
}

export function fetchPromotions(): Promise<Promotion[]> {
  return apiRequest<Promotion[]>('/api/promotions')
}

export function fetchProductPromotions(
  productId: number,
): Promise<ProductPromotion[]> {
  return apiRequest<ProductPromotion[]>(
    `/api/promotions/products/${productId}`,
  )
}

export function fetchPromotion(promotionId: number): Promise<Promotion> {
  return apiRequest<Promotion>(`/api/promotions/${promotionId}`)
}

export function createPromotion(
  payload: PromotionCreateRequest,
): Promise<Promotion> {
  return apiRequest<Promotion>('/api/promotions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updatePromotion(
  promotionId: number,
  payload: PromotionCreateRequest,
): Promise<Promotion> {
  return apiRequest<Promotion>(`/api/promotions/${promotionId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function fetchPromotionProducts(
  promotionId: number,
): Promise<PromotionProduct[]> {
  return apiRequest<PromotionProduct[]>(
    `/api/promotions/${promotionId}/products`,
  )
}

export function replacePromotionProducts(
  promotionId: number,
  productIds: number[],
): Promise<PromotionProduct[]> {
  return apiRequest<PromotionProduct[]>(
    `/api/promotions/${promotionId}/products`,
    {
      method: 'PUT',
      body: JSON.stringify({
        product_ids: productIds,
      } satisfies PromotionProductsRequest),
    },
  )
}

export function addPromotionProduct(
  promotionId: number,
  productId: number,
): Promise<PromotionProduct> {
  return apiRequest<PromotionProduct>(
    `/api/promotions/${promotionId}/products`,
    {
      method: 'POST',
      body: JSON.stringify({
        product_id: productId,
      }),
    },
  )
}

export function fetchPromotionGroups(
  promotionId: number,
): Promise<PromotionGroup[]> {
  return apiRequest<PromotionGroup[]>(
    `/api/promotions/${promotionId}/groups`,
  )
}

export function createPromotionGroup(
  promotionId: number,
  payload: PromotionGroupRequest,
): Promise<PromotionGroup> {
  return apiRequest<PromotionGroup>(
    `/api/promotions/${promotionId}/groups`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function updatePromotionGroup(
  groupId: number,
  payload: PromotionGroupRequest,
): Promise<PromotionGroup> {
  return apiRequest<PromotionGroup>(
    `/api/promotions/groups/${groupId}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
  )
}

export async function deletePromotionGroup(
  groupId: number,
): Promise<void> {
  const response = await fetch(`/api/promotions/groups/${groupId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...(window.localStorage.getItem('computerstore_access_token')
        ? {
            Authorization: `Bearer ${window.localStorage.getItem(
              'computerstore_access_token',
            )}`,
          }
        : {}),
    },
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`

    try {
      const payload = (await response.json()) as {
        detail?: string | Array<{ msg?: string }>
      }

      if (typeof payload.detail === 'string') {
        detail = payload.detail
      }

      if (Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((item) => item.msg ?? 'Invalid value')
          .join(', ')
      }
    } catch {
      // Keep the status fallback.
    }

    throw new Error(detail)
  }
}

export function fetchPromotionBenefits(
  groupId: number,
): Promise<PromotionBenefit[]> {
  return apiRequest<PromotionBenefit[]>(
    `/api/promotions/groups/${groupId}/benefits`,
  )
}

export function createProductBenefit(
  groupId: number,
  payload: ProductBenefitRequest,
): Promise<PromotionBenefit> {
  return apiRequest<PromotionBenefit>(
    `/api/promotions/groups/${groupId}/benefits/product`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function createWarrantyBenefit(
  groupId: number,
  payload: WarrantyBenefitRequest,
): Promise<PromotionBenefit> {
  return apiRequest<PromotionBenefit>(
    `/api/promotions/groups/${groupId}/benefits/warranty`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function createCashbackBenefit(
  groupId: number,
  payload: CashbackBenefitRequest,
): Promise<PromotionBenefit> {
  return apiRequest<PromotionBenefit>(
    `/api/promotions/groups/${groupId}/benefits/cashback`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}