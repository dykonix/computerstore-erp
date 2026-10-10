from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.repositories.customer_repository import CustomerRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.promotion_repository import PromotionRepository
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

        gst_rate = (
            category.gst_rate
            if category is not None
            and category.gst_rate is not None
            else Decimal("0.00")
        )

        gst_rate = Decimal(gst_rate).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        discount_amount = (
            Decimal("0.00")
            if is_free_product
            else (configured_unit_price - actual_unit_price) * quantity
        )

        if discount_amount < Decimal("0.00"):
            discount_amount = Decimal("0.00")

        discount_amount = discount_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        line_total = (
            actual_unit_price * quantity
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # Selling prices are GST-inclusive.
        #
        # GST = inclusive price * GST rate / (100 + GST rate)
        if gst_rate > Decimal("0.00") and line_total > Decimal("0.00"):
            gst_amount = (
                line_total
                * gst_rate
                / (Decimal("100.00") + gst_rate)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        else:
            gst_amount = Decimal("0.00")

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product_id,
            promotion_id=promotion_id,
            promotion_name=promotion_name,
            promotion_cashback_amount=promotion_cashback_amount,
            quantity=quantity,
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

        self.sale_repository.create_sale_item(
            session,
            sale_item,
        )

        self._recalculate_sale_totals(
            session,
            sale,
        )

        session.flush()

        return sale_item

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

        sale.status = "DELIVERED"
        session.flush()
        return sale