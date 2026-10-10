from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product_price import ProductPrice
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment


class SaleRepository:
    def create_sale(self, session: Session, sale: Sale) -> Sale:
        session.add(sale)
        session.flush()
        return sale

    def get_sale(
        self,
        session: Session,
        tenant_id: int,
        sale_id: int,
        lock: bool = False,
    ) -> Sale | None:
        statement = select(Sale).where(
            Sale.id == sale_id,
            Sale.tenant_id == tenant_id,
        )

        if lock:
            statement = statement.with_for_update()

        return session.scalar(statement)

    def list_sale_items(
        self,
        session: Session,
        sale_id: int,
    ) -> list[SaleItem]:
        statement = (
            select(SaleItem)
            .where(SaleItem.sale_id == sale_id)
            .order_by(SaleItem.id)
        )

        return list(session.scalars(statement))

    def get_current_product_price(
        self,
        session: Session,
        product_id: int,
        effective_date: date,
    ) -> ProductPrice | None:
        statement = (
            select(ProductPrice)
            .where(
                ProductPrice.product_id == product_id,
                ProductPrice.valid_from <= effective_date,
                (
                    (ProductPrice.valid_to.is_(None))
                    | (ProductPrice.valid_to >= effective_date)
                ),
            )
            .order_by(ProductPrice.valid_from.desc(), ProductPrice.id.desc())
            .limit(1)
        )

        return session.scalar(statement)

    def get_category(
        self,
        session: Session,
        category_id: int,
    ) -> Category | None:
        statement = select(Category).where(
            Category.id == category_id,
        )

        return session.scalar(statement)

    def get_sale_item_for_product(
        self,
        session: Session,
        sale_id: int,
        product_id: int,
    ) -> SaleItem | None:
        statement = select(SaleItem).where(
            SaleItem.sale_id == sale_id,
            SaleItem.product_id == product_id,
        )

        return session.scalar(statement)

    def create_sale_item(
        self,
        session: Session,
        sale_item: SaleItem,
    ) -> SaleItem:
        session.add(sale_item)
        session.flush()
        return sale_item

    def create_sale_payment(
        self,
        session: Session,
        sale_payment: SalePayment,
    ) -> SalePayment:
        session.add(sale_payment)
        session.flush()
        return sale_payment

    def list_sale_payments(
        self,
        session: Session,
        sale_id: int,
    ) -> list[SalePayment]:
        statement = (
            select(SalePayment)
            .where(SalePayment.sale_id == sale_id)
            .order_by(SalePayment.id)
        )

        return list(session.scalars(statement))

    def get_sale_payment_total(
        self,
        session: Session,
        sale_id: int,
    ) -> Decimal:
        statement = select(
            func.coalesce(
                func.sum(SalePayment.amount),
                Decimal("0.00"),
            )
        ).where(
            SalePayment.sale_id == sale_id,
        )

        total = session.scalar(statement)

        return Decimal(total or "0.00")