from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.inventory_repository import InventoryRepository
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

        existing_item = self.sale_repository.get_sale_item_for_product(
            session,
            sale.id,
            product_id,
        )

        if existing_item is not None:
            raise ValueError(
                "Product is already present in this sale"
            )

        today = date.today()

        current_price = self.sale_repository.get_current_product_price(
            session,
            product_id,
            today,
        )

        if current_price is None:
            raise ValueError(
                "No active price found for product"
            )

        configured_unit_price = current_price.sale_price

        if actual_unit_price is None:
            actual_unit_price = configured_unit_price

        actual_unit_price = Decimal(actual_unit_price)

        if actual_unit_price < 0:
            raise ValueError(
                "Actual unit price cannot be negative"
            )

        category = self.sale_repository.get_category(
            session,
            product.category_id,
        )

        gst_rate = (
            category.gst_rate
            if category is not None and category.gst_rate is not None
            else Decimal("0.00")
        )

        discount_amount = (
            configured_unit_price - actual_unit_price
        ) * quantity

        if discount_amount < 0:
            discount_amount = Decimal("0.00")

        line_total = (
            actual_unit_price * quantity
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        gst_amount = (
            line_total * gst_rate / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product_id,
            quantity=quantity,
            configured_unit_price=configured_unit_price,
            actual_unit_price=actual_unit_price,
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

        invoice_discount = sale.invoice_discount or Decimal("0.00")

        if invoice_discount > subtotal:
            raise ValueError(
                "Invoice discount cannot exceed sale subtotal"
            )

        taxable_amount = subtotal - invoice_discount

        gst_amount = sum(
            (
                item.gst_amount
                for item in sale_items
            ),
            Decimal("0.00"),
        )

        total_amount = taxable_amount + gst_amount

        sale.subtotal = subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale.taxable_amount = taxable_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale.gst_amount = gst_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        sale.total_amount = total_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

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

        if sale.customer_id is None:
            raise ValueError(
                "Customer is required before reservation"
            )

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
                self.inventory_repository.get_inventory_at_location(
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