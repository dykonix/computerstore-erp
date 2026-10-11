from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.models.promotion_benefit import PromotionBenefit
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.models.product_serial_number import ProductSerialNumber
from app.repositories.customer_repository import CustomerRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.promotion_repository import PromotionRepository
from app.repositories.product_serial_number_repository import ProductSerialNumberRepository
from app.repositories.sale_repository import SaleRepository
from app.services.auth_service import AuthService
from app.services.authorization_service import AuthorizationService


class SaleService:

    def __init__(
        self,
        sale_repository=None,
        inventory_repository=None,
        customer_repository=None,
        auth_service=None,
        authorization_service=None,
        promotion_repository=None,
        product_serial_number_repository=None,
    ):
        self.sale_repository = sale_repository or SaleRepository()
        self.inventory_repository = (
            inventory_repository or InventoryRepository()
        )
        self.customer_repository = (
            customer_repository or CustomerRepository()
        )
        self.auth_service = auth_service or AuthService()
        self.authorization_service = (
            authorization_service or AuthorizationService()
        )
        self.promotion_repository = (
            promotion_repository or PromotionRepository()
        )
        self.product_serial_number_repository = (
            product_serial_number_repository or ProductSerialNumberRepository()
        )

    def get_sale(
        self,
        session,
        current_user,
        sale_id,
    ):
        tenant_id = current_user.tenant_id

        return self.sale_repository.get_sale(
            session,
            tenant_id,
            sale_id,
        )

    def get_product_availability(
        self,
        session,
        current_user,
        store_id,
        product_id,
    ):
        tenant_id = current_user.tenant_id

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            store_id,
        )

        product = self.inventory_repository.get_product(
            session, tenant_id, product_id
        )
        if product is None:
            raise ValueError("Product not found")

        authorized_store_ids = {
            store.id
            for store in self.authorization_service.list_allowed_stores(
                session, current_user, "sell"
            )
        }

        current = None
        others = []
        for inventory, location_type, location_name in (
            self.inventory_repository.list_product_balances(
                session, tenant_id, product_id
            )
        ):
            available = inventory.quantity - inventory.reserved_quantity
            entry = {
                "location_type": location_type,
                "location_name": location_name,
                "quantity": inventory.quantity,
                "reserved_quantity": inventory.reserved_quantity,
                "available_quantity": available,
            }
            if inventory.store_id == store_id:
                current = entry
            elif available > 0 and (
                inventory.godown_id is not None
                or inventory.store_id in authorized_store_ids
            ):
                others.append(entry)

        if current is None:
            store = self.inventory_repository.get_store(
                session, tenant_id, store_id
            )
            current = {
                "location_type": "Store",
                "location_name": store.name if store is not None else "",
                "quantity": 0,
                "reserved_quantity": 0,
                "available_quantity": 0,
            }

        return {"current_store": current, "other_locations": others}

    def create_sale(
        self,
        session,
        current_user,
        store_id,
        customer_id=None,
    ):
        tenant_id = current_user.tenant_id

        employee = self.auth_service.get_employee_for_user(
            session,
            current_user,
        )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            store_id,
        )

        if customer_id is not None:
            customer = self.customer_repository.get_customer(
                session,
                tenant_id,
                customer_id,
            )

            if customer is None:
                raise ValueError("Customer not found")

            if not customer.is_active:
                raise ValueError(
                    "Inactive customers cannot be used for new sales"
                )

        sale = Sale(
            tenant_id=tenant_id,
            store_id=store_id,
            customer_id=customer_id,
            employee_id=employee.id,
            status="DRAFT",
            subtotal=Decimal("0.00"),
            invoice_discount=Decimal("0.00"),
            taxable_amount=Decimal("0.00"),
            gst_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            payable_amount=Decimal("0.00"),
        )

        return self.sale_repository.create_sale(
            session,
            sale,
        )

    def add_sale_item(
        self,
        session,
        current_user,
        sale_id,
        product_id,
        quantity,
        actual_unit_price=None,
        configured_minimum_price=Decimal("0.00"),
        minimum_price_override=False,
        is_free_product=False,
        promotion_id=None,
        promotion_benefit_ids=None,
        promotion_benefit_ids_by_unit=None,
        promotion_benefit_sources_by_unit=None,
    ):
        tenant_id = current_user.tenant_id

        sale = self.sale_repository.get_sale(
            session,
            tenant_id,
            sale_id,
            lock=True,
        )

        if sale is None:
            raise ValueError("Sale not found")

        if sale.status != "DRAFT":
            raise ValueError(
                "Sale items can only be added to draft sales"
            )

        if quantity <= 0:
            raise ValueError(
                "Sale item quantity must be greater than zero"
            )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        product = self.inventory_repository.get_product(
            session,
            tenant_id,
            product_id,
        )

        if product is None:
            raise ValueError("Product not found")

        if not product.is_active:
            raise ValueError(
                "Inactive products cannot be added to a sale"
            )

        existing_item = (
            self.sale_repository.get_sale_item_for_product(
                session,
                sale.id,
                product_id,
            )
        )

        if existing_item is not None:
            raise ValueError(
                "Product is already present in this sale"
            )

        inventory = self.inventory_repository.get_inventory_at_location(
            session,
            tenant_id,
            product_id,
            sale.store_id,
            None,
        )
        if inventory is None:
            raise ValueError(
                "Inventory not found for product at the selected store"
            )

        available_quantity = (
            inventory.quantity - inventory.reserved_quantity
        )
        if quantity > available_quantity:
            raise ValueError(
                "Sale item quantity exceeds available inventory"
            )

        today = date.today()

        current_price = (
            self.sale_repository.get_current_product_price(
                session,
                product_id,
                today,
            )
        )

        if current_price is None:
            raise ValueError(
                "No active price found for product"
            )

        promotion_name = None
        promotion_cashback_amount = Decimal("0.00")
        unit_benefits: list[list[tuple[PromotionBenefit, str]]] = []
        unit_cashback: list[Decimal] = []
        split_units = promotion_benefit_ids_by_unit is not None
        if promotion_id is not None:
            selected_promotion = (
                self.promotion_repository.get_active_for_product(
                    session,
                    tenant_id,
                    promotion_id,
                    product_id,
                    date.today(),
                )
            )
            if selected_promotion is None:
                raise ValueError(
                    "Promotion is not active for this product"
                )
            promotion, promotion_cashback_amount = selected_promotion
            promotion_name = promotion.name
            promotion_cashback_amount = Decimal(
                promotion_cashback_amount or "0.00"
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            if split_units:
                source_rows = promotion_benefit_sources_by_unit or [
                    {} for _ in promotion_benefit_ids_by_unit
                ]
                for unit_index, benefit_ids in enumerate(promotion_benefit_ids_by_unit):
                    selected_product_benefits, selected_cashback = (
                        self._validate_selected_promotion_benefits(
                            session=session,
                            tenant_id=tenant_id,
                            promotion_id=promotion_id,
                            selected_benefit_ids=benefit_ids,
                        )
                    )
                    cashback_for_unit = (
                        selected_cashback
                        if selected_cashback is not None
                        else promotion_cashback_amount if unit_index == 0
                        else Decimal("0.00")
                    )
                    unit_cashback.append(cashback_for_unit)
                    source_by_benefit = source_rows[unit_index]
                    selected_sources = {benefit.id for benefit in selected_product_benefits}
                    if set(source_by_benefit) - selected_sources:
                        raise ValueError("A fulfillment source was provided for an unselected product benefit")
                    unit_benefits.append(
                        [
                            (benefit, source_by_benefit.get(benefit.id, "MANUFACTURER"))
                            for benefit in selected_product_benefits
                        ]
                    )
                promotion_cashback_amount = sum(
                    unit_cashback, Decimal("0.00")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                selected_product_benefits, selected_cashback = (
                    self._validate_selected_promotion_benefits(
                        session=session,
                        tenant_id=tenant_id,
                        promotion_id=promotion_id,
                        selected_benefit_ids=promotion_benefit_ids or [],
                    )
                )
                if selected_cashback is not None:
                    promotion_cashback_amount = selected_cashback
                unit_benefits = [[
                    (benefit, "MANUFACTURER")
                    for benefit in selected_product_benefits
                ]]
                unit_cashback = [promotion_cashback_amount]
        elif promotion_benefit_ids or promotion_benefit_ids_by_unit is not None:
            raise ValueError("Promotion benefits require a selected promotion")

        if not unit_benefits:
            unit_benefits = [[]]

        configured_unit_price = Decimal(
            current_price.sale_price
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # ProductPrice.minimum_sale_price is the authoritative
        # minimum selling price for the product.
        minimum_price = (
            Decimal(current_price.minimum_sale_price)
            if current_price.minimum_sale_price is not None
            else Decimal("0.00")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if minimum_price > configured_unit_price:
            raise ValueError(
                "Minimum sale price cannot exceed configured sale price"
            )

        if is_free_product:
            actual_unit_price = Decimal("0.00")
        elif actual_unit_price is None:
            actual_unit_price = configured_unit_price
        else:
            actual_unit_price = Decimal(
                actual_unit_price
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        if actual_unit_price < Decimal("0.00"):
            raise ValueError(
                "Actual unit price cannot be negative"
            )

        if (
            not is_free_product
            and minimum_price > Decimal("0.00")
            and actual_unit_price < minimum_price
            and not minimum_price_override
        ):
            raise ValueError(
                "Actual unit price is below the minimum sale price; "
                "minimum price override is required"
            )

        if (
            is_free_product
            and minimum_price_override
        ):
            minimum_price_override = False

        category = self.sale_repository.get_category(
            session,
            product.category_id,
        )
        if category is None or category.gst_rate is None:
            category_label = category.name if category is not None else product.category_id
            raise ValueError(
                f"GST rate is not configured for category '{category_label}' of product {product.name}"
            )

        gst_rate = category.gst_rate

        gst_rate = Decimal(gst_rate).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale_items = []
        unit_count = quantity if split_units else 1
        for unit_index in range(unit_count):
            item_quantity = 1 if split_units else quantity
            cashback_amount = (
                unit_cashback[unit_index]
                if split_units
                else promotion_cashback_amount
            )
            discount_amount = (
                Decimal("0.00")
                if is_free_product
                else max(configured_unit_price - actual_unit_price, Decimal("0.00"))
                * item_quantity
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_total = (actual_unit_price * item_quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            _, gst_amount = self._extract_inclusive_gst(line_total, gst_rate)
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product_id,
                promotion_id=promotion_id,
                promotion_name=promotion_name,
                promotion_cashback_amount=cashback_amount,
                quantity=item_quantity,
                configured_unit_price=configured_unit_price,
                configured_minimum_price=minimum_price,
                actual_unit_price=actual_unit_price,
                minimum_price_override=minimum_price_override,
                is_free_product=is_free_product,
                cost_price=current_price.cost_price,
                gst_rate=gst_rate,
                gst_amount=gst_amount,
                discount_amount=discount_amount,
                line_total=line_total,
            )
            self.sale_repository.create_sale_item(session, sale_item)
            sale_items.append(sale_item)

            for benefit, fulfillment_source in unit_benefits[unit_index]:
                self._create_promotion_benefit_sale_item(
                    session=session,
                    sale=sale,
                    source_sale_item=sale_item,
                    benefit=benefit,
                    promotion_name=promotion_name,
                    fulfillment_source=fulfillment_source,
                )

        self._recalculate_sale_totals(
            session,
            sale,
        )

        session.flush()

        return sale_items[0]

    @staticmethod
    def _extract_inclusive_gst(
        inclusive_amount: Decimal, gst_rate: Decimal
    ) -> tuple[Decimal, Decimal]:
        if gst_rate < 0:
            raise ValueError("GST rate cannot be negative")
        if inclusive_amount == 0 or gst_rate == 0:
            return inclusive_amount, Decimal("0.00")
        taxable_amount = (inclusive_amount * Decimal("100.00") / (
            Decimal("100.00") + gst_rate
        )).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return taxable_amount, (inclusive_amount - taxable_amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _validate_selected_promotion_benefits(
        self,
        *,
        session,
        tenant_id: int,
        promotion_id: int,
        selected_benefit_ids: list[int],
    ):
        groups = self.promotion_repository.list_groups(
            session, tenant_id, promotion_id
        )
        selected_ids = set(selected_benefit_ids)
        known_ids: set[int] = set()
        selected_products = []
        selected_cashback = Decimal("0.00")
        has_mapped_groups = False

        for group in groups:
            benefits = self.promotion_repository.list_benefits(
                session, tenant_id, group.id
            )
            group_benefits = benefits
            group_ids = {benefit.id for benefit in group_benefits}
            known_ids.update(group_ids)
            selected_group_benefits = [
                benefit for benefit in group_benefits if benefit.id in selected_ids
            ]

            if group.group_requirement is None or group.benefit_selection_rule is None:
                if any(benefit.id in selected_ids for benefit in benefits):
                    raise ValueError(
                        f"Promotion group '{group.name}' requires explicit rule mapping"
                    )
                selected_cashback += sum(
                    (
                        benefit.cashback_amount or Decimal("0.00")
                        for benefit in benefits
                        if benefit.benefit_type == "CASHBACK"
                        and str(benefit.payment_mode).upper() == "UPI"
                    ),
                    Decimal("0.00"),
                )
                continue

            has_mapped_groups = True
            chosen_count = len(selected_group_benefits)
            all_count = len(group_benefits)
            rule = group.benefit_selection_rule
            required = group.group_requirement == "REQUIRED"

            if required and chosen_count == 0:
                raise ValueError(f"Select a benefit for required group '{group.name}'")
            if rule == "ONE" and chosen_count > 1:
                raise ValueError(f"Select exactly one benefit for group '{group.name}'")
            if rule == "ONE" and required and chosen_count != 1:
                raise ValueError(f"Select exactly one benefit for group '{group.name}'")
            if rule == "ANY" and required and chosen_count == 0:
                raise ValueError(f"Select at least one benefit for group '{group.name}'")
            if rule == "ALL" and chosen_count not in {0, all_count}:
                raise ValueError(f"Select all benefits for group '{group.name}'")
            if rule == "ALL" and required and chosen_count != all_count:
                raise ValueError(f"Select all benefits for group '{group.name}'")

            for benefit in selected_group_benefits:
                if benefit.benefit_type == "PRODUCT":
                    selected_products.append(benefit)
                elif (
                    benefit.benefit_type == "CASHBACK"
                    and str(benefit.payment_mode).upper() == "UPI"
                ):
                    selected_cashback += benefit.cashback_amount or Decimal("0.00")
                elif benefit.benefit_type == "WARRANTY":
                    raise ValueError(
                        "Warranty benefits cannot yet be added as sale lines"
                    )

        if selected_ids - known_ids:
            raise ValueError("A selected benefit does not belong to this promotion")

        if not has_mapped_groups:
            return selected_products, None
        return selected_products, selected_cashback.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def _create_promotion_benefit_sale_item(
        self,
        *,
        session,
        sale,
        source_sale_item,
        benefit,
        promotion_name: str | None,
        fulfillment_source: str = "MANUFACTURER",
    ) -> SaleItem:
        product = self.inventory_repository.get_product(
            session, sale.tenant_id, benefit.product_id
        )
        if product is None or not product.is_active:
            raise ValueError("Promotion benefit product is missing or inactive")

        current_price = self.sale_repository.get_current_product_price(
            session, product.id, date.today()
        )
        configured_price = Decimal(benefit.promotion_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        actual_price = configured_price
        cost_price = (
            Decimal(current_price.cost_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if current_price is not None
            else Decimal("0.00")
        )
        category = self.sale_repository.get_category(session, product.category_id)
        if category is None or category.gst_rate is None:
            category_label = category.name if category is not None else product.category_id
            raise ValueError(
                f"GST rate is not configured for category '{category_label}' of promotion benefit {product.name}"
            )
        gst_rate = Decimal(category.gst_rate).quantize(Decimal("0.01"))
        line_total = (actual_price * source_sale_item.quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        _, gst_amount = self._extract_inclusive_gst(line_total, gst_rate)
        product_price = (
            Decimal(current_price.sale_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if current_price is not None
            else configured_price
        )
        discount_amount = max(product_price - actual_price, Decimal("0.00"))
        discount_amount = (discount_amount * source_sale_item.quantity).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if fulfillment_source == "STORE":
            inventory = self.inventory_repository.get_inventory_at_location(
                session,
                sale.tenant_id,
                product.id,
                sale.store_id,
                None,
            )
            if inventory is None:
                raise ValueError(
                    f"Store inventory is not configured for promotion benefit {product.name}"
                )

        benefit_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            promotion_id=source_sale_item.promotion_id,
            promotion_name=promotion_name,
            promotion_benefit_id=benefit.id,
            promotion_benefit_name=product.name,
            promotion_source_sale_item_id=source_sale_item.id,
            is_promotion_benefit=True,
            promotion_benefit_source=fulfillment_source,
            promotion_cashback_amount=Decimal("0.00"),
            quantity=source_sale_item.quantity,
            configured_unit_price=product_price,
            configured_minimum_price=Decimal("0.00"),
            actual_unit_price=actual_price,
            minimum_price_override=False,
            is_free_product=actual_price == Decimal("0.00"),
            cost_price=cost_price,
            gst_rate=gst_rate,
            gst_amount=gst_amount,
            discount_amount=discount_amount,
            line_total=line_total,
        )
        return self.sale_repository.create_sale_item(session, benefit_item)

    def _recalculate_sale_totals(
        self,
        session,
        sale,
    ):
        sale_items = self.sale_repository.list_sale_items(
            session,
            sale.id,
        )

        subtotal = sum(
            (
                item.line_total
                for item in sale_items
            ),
            Decimal("0.00"),
        )

        subtotal = subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        invoice_discount = (
            sale.invoice_discount
            or Decimal("0.00")
        )

        invoice_discount = Decimal(
            invoice_discount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if invoice_discount > subtotal:
            raise ValueError(
                "Invoice discount cannot exceed sale subtotal"
            )

        gst_amount = sum(
            (
                item.gst_amount
                for item in sale_items
            ),
            Decimal("0.00"),
        )

        gst_amount = gst_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        cashback_amount = sum(
            (
                item.promotion_cashback_amount
                for item in sale_items
            ),
            Decimal("0.00"),
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        amount_before_cashback = subtotal - invoice_discount
        if cashback_amount > amount_before_cashback:
            raise ValueError(
                "Promotion cashback cannot exceed the sale amount"
            )

        taxable_amount = max(
            Decimal("0.00"),
            subtotal - invoice_discount - gst_amount,
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # Line totals already include GST; cashback reduces payable only.
        total_amount = amount_before_cashback.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        payable_amount = (total_amount - cashback_amount).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale.subtotal = subtotal
        sale.taxable_amount = taxable_amount
        sale.gst_amount = gst_amount
        sale.cashback_amount = cashback_amount
        sale.total_amount = total_amount
        sale.payable_amount = payable_amount

        session.flush()

    def reserve_sale(
        self,
        session,
        current_user,
        sale_id,
    ):
        tenant_id = current_user.tenant_id

        sale = self.sale_repository.get_sale(
            session,
            tenant_id,
            sale_id,
            lock=True,
        )

        if sale is None:
            raise ValueError("Sale not found")

        if sale.status != "DRAFT":
            raise ValueError(
                "Only draft sales can be reserved"
            )

        employee = self.auth_service.get_employee_for_user(
            session,
            current_user,
        )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        if sale.customer_id is not None:
            customer = self.customer_repository.get_customer(
                session,
                tenant_id,
                sale.customer_id,
            )

            if customer is None:
                raise ValueError("Customer not found")

            if not customer.is_active:
                raise ValueError(
                    "Inactive customers cannot be used for new sales"
                )

        sale_items = self.sale_repository.list_sale_items(
            session,
            sale.id,
        )

        if not sale_items:
            raise ValueError(
                "Sale must contain at least one item"
            )

        for item in sale_items:
            if (
                item.is_promotion_benefit
                and item.promotion_benefit_source == "MANUFACTURER"
            ):
                continue

            inventory = (
                self.inventory_repository
                .get_inventory_at_location(
                    session,
                    tenant_id,
                    item.product_id,
                    sale.store_id,
                    None,
                    lock=True,
                )
            )

            if inventory is None:
                raise ValueError(
                    f"Inventory not found for product {item.product_id}"
                )

            self.inventory_repository.reserve_inventory(
                session,
                tenant_id,
                inventory,
                item.quantity,
            )

            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=item.product_id,
                movement_type="RESERVATION",
                from_store_id=sale.store_id,
                reference_type="SALE",
                reference_id=sale.id,
                performed_by_employee_id=employee.id,
                notes=f"Inventory reserved for sale {sale.id}",
                quantity=item.quantity,
            )

            self.inventory_repository.add_movement(
                session,
                movement,
            )

        now = datetime.now(timezone.utc)

        sale.status = "RESERVED"
        sale.reserved_at = now
        sale.reservation_warning_at = (
            now + timedelta(minutes=10)
        )
        sale.reservation_expires_at = (
            now + timedelta(minutes=60)
        )

        session.flush()

        return sale

    def add_sale_payment(
        self,
        session,
        current_user,
        sale_id,
        payment_mode,
        amount,
        transaction_reference=None,
    ):
        tenant_id = current_user.tenant_id

        sale = self.sale_repository.get_sale(
            session,
            tenant_id,
            sale_id,
            lock=True,
        )

        if sale is None:
            raise ValueError("Sale not found")

        if sale.status != "RESERVED":
            raise ValueError(
                "Payments can only be recorded for reserved sales"
            )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        if payment_mode is None or not str(payment_mode).strip():
            raise ValueError("Payment mode is required")

        payment_mode = str(payment_mode).strip().upper()

        try:
            amount = Decimal(str(amount))
        except Exception as exc:
            raise ValueError(
                "Payment amount must be valid"
            ) from exc

        amount = amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if amount <= 0:
            raise ValueError(
                "Payment amount must be greater than zero"
            )

        paid_total = (
            self.sale_repository.get_sale_payment_total(
                session,
                sale.id,
            )
        )

        remaining_amount = (
            sale.payable_amount - paid_total
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if amount > remaining_amount:
            raise ValueError(
                "Payment amount cannot exceed remaining sale amount"
            )

        if transaction_reference is not None:
            transaction_reference = str(
                transaction_reference
            ).strip()

            if not transaction_reference:
                transaction_reference = None

        if payment_mode != "CASH" and transaction_reference is None:
            raise ValueError(
                "Transaction reference is required for this payment mode"
            )

        sale_payment = SalePayment(
            sale_id=sale.id,
            payment_mode=payment_mode,
            amount=amount,
            transaction_reference=transaction_reference,
        )

        self.sale_repository.create_sale_payment(
            session,
            sale_payment,
        )

        session.flush()

        return sale_payment

    def confirm_sale(
        self,
        session,
        current_user,
        sale_id,
    ):
        """
        Confirm a reserved sale after full payment.

        Confirmation:
        1. Locks the sale.
        2. Verifies the sale is RESERVED.
        3. Verifies the full sale amount has been paid.
        4. Locks the relevant inventory rows.
        5. Converts reserved inventory into sold inventory.
        6. Creates SALE inventory movements.
        7. Changes the sale status to CONFIRMED.

        Serial-number assignment is intentionally not handled here.
        That belongs to the later delivery slice.
        """

        tenant_id = current_user.tenant_id

        sale = self.sale_repository.get_sale(
            session,
            tenant_id,
            sale_id,
            lock=True,
        )

        if sale is None:
            raise ValueError("Sale not found")

        if sale.status != "RESERVED":
            raise ValueError(
                "Only reserved sales can be confirmed"
            )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        paid_total = (
            self.sale_repository.get_sale_payment_total(
                session,
                sale.id,
            )
        )

        paid_total = paid_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale_total = (
            sale.payable_amount
            or Decimal("0.00")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if paid_total != sale_total:
            raise ValueError(
                "Sale cannot be confirmed until full payment is received"
            )

        if sale.cashback_amount > Decimal("0.00"):
            payments = self.sale_repository.list_sale_payments(
                session,
                sale.id,
            )
            if not any(
                payment.payment_mode.strip().upper() == "UPI"
                for payment in payments
            ):
                raise ValueError(
                    "UPI cashback requires a UPI payment"
                )

        employee = self.auth_service.get_employee_for_user(
            session,
            current_user,
        )

        sale_items = self.sale_repository.list_sale_items(
            session,
            sale.id,
        )

        if not sale_items:
            raise ValueError(
                "Sale must contain at least one item"
            )

        for item in sale_items:
            if (
                item.is_promotion_benefit
                and item.promotion_benefit_source == "MANUFACTURER"
            ):
                continue

            inventory = (
                self.inventory_repository
                .get_inventory_at_location(
                    session,
                    tenant_id,
                    item.product_id,
                    sale.store_id,
                    None,
                    lock=True,
                )
            )

            if inventory is None:
                raise ValueError(
                    f"Inventory not found for product {item.product_id}"
                )

            if inventory.reserved_quantity < item.quantity:
                raise ValueError(
                    f"Reserved inventory is insufficient for product "
                    f"{item.product_id}"
                )

            if inventory.quantity < item.quantity:
                raise ValueError(
                    f"Physical inventory is insufficient for product "
                    f"{item.product_id}"
                )

            inventory.quantity -= item.quantity
            inventory.reserved_quantity -= item.quantity

            movement = InventoryMovement(
                tenant_id=tenant_id,
                product_id=item.product_id,
                movement_type="SALE",
                from_store_id=sale.store_id,
                reference_type="SALE",
                reference_id=sale.id,
                performed_by_employee_id=employee.id,
                notes=f"Inventory sold for sale {sale.id}",
                quantity=item.quantity,
            )

            self.inventory_repository.add_movement(
                session,
                movement,
            )

        sale.status = "CONFIRMED"

        session.flush()

        return sale

    def list_sale_payments(
        self,
        session,
        current_user,
        sale_id,
    ):
        sale = self.sale_repository.get_sale(
            session,
            current_user.tenant_id,
            sale_id,
        )
        if sale is None:
            raise ValueError("Sale not found")

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        return self.sale_repository.list_sale_payments(
            session,
            sale.id,
        )

    def deliver_sale(
        self,
        session,
        current_user,
        sale_id,
        serial_numbers_by_item=None,
        allow_missing_serial_numbers=True,
    ):
        sale = self.sale_repository.get_sale(
            session,
            current_user.tenant_id,
            sale_id,
            lock=True,
        )
        if sale is None:
            raise ValueError("Sale not found")

        if sale.status != "CONFIRMED":
            raise ValueError(
                "Only confirmed sales can be delivered"
            )

        self.authorization_service.require_permission(
            session,
            current_user,
            "sell",
            sale.store_id,
        )

        sale_items = self.sale_repository.list_sale_items(session, sale.id)
        item_ids = {item.id for item in sale_items}
        supplied = serial_numbers_by_item or {}
        if set(supplied) - item_ids:
            raise ValueError("Serial numbers reference an item outside this sale")

        for item in sale_items:
            product = self.inventory_repository.get_product(
                session, sale.tenant_id, item.product_id
            )
            if product is None:
                raise ValueError("Sale product does not belong to the current tenant")
            existing_serials = self.sale_repository.list_sale_item_serials(
                session, item.id
            )
            if not product.requires_serial_number:
                if supplied.get(item.id):
                    raise ValueError(
                        f"Product {product.name} does not require serial numbers"
                    )
                continue

            incoming_serials = [
                str(value).strip() for value in supplied.get(item.id, [])
            ]
            if any(not value for value in incoming_serials):
                raise ValueError("Serial numbers cannot be blank")
            if len(incoming_serials) != len(set(incoming_serials)):
                raise ValueError("Duplicate serial numbers are not allowed")
            missing_count = item.quantity - len(existing_serials) - len(incoming_serials)
            if len(existing_serials) + len(incoming_serials) > item.quantity:
                raise ValueError(
                    f"Too many serial numbers for product {product.name}"
                )
            if missing_count > 0 and not allow_missing_serial_numbers:
                raise ValueError(
                    f"Serial numbers are missing for {product.name}: "
                    f"{missing_count} unit(s)"
                )

            for serial_value in incoming_serials:
                serial = self.product_serial_number_repository.get_by_serial_number(
                    session,
                    sale.tenant_id,
                    serial_value,
                    lock=True,
                )
                if serial is None:
                    serial = self.product_serial_number_repository.create(
                        session,
                        ProductSerialNumber(
                            tenant_id=sale.tenant_id,
                            product_id=product.id,
                            serial_number=serial_value,
                            status="SOLD",
                        ),
                    )
                else:
                    if serial.product_id != product.id:
                        raise ValueError(
                            f"Serial number {serial_value} belongs to another product"
                        )
                    if serial.status != "IN_STOCK":
                        raise ValueError(
                            f"Serial number {serial_value} is not available for delivery"
                        )
                    if self.sale_repository.get_sale_item_serial_assignment(
                        session, serial.id
                    ) is not None:
                        raise ValueError(
                            f"Serial number {serial_value} is already assigned to a sale"
                        )
                    self.product_serial_number_repository.update_status(
                        session, serial, "SOLD"
                    )
                self.sale_repository.add_sale_item_serial(
                    session, item.id, serial.id
                )

        sale.status = "DELIVERED"
        session.flush()
        return sale