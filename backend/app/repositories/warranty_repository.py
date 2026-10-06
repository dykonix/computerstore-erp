from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.warranty_option import WarrantyOption
from app.models.warranty_price import WarrantyPrice


class WarrantyRepository:
    def get_product(
        self, session: Session, tenant_id: int, product_id: int
    ) -> Product | None:
        return session.scalar(
            select(Product).where(
                Product.id == product_id, Product.tenant_id == tenant_id
            )
        )

    def get_option(
        self, session: Session, tenant_id: int, option_id: int
    ) -> WarrantyOption | None:
        statement = (
            select(WarrantyOption)
            .join(Product, Product.id == WarrantyOption.product_id)
            .where(
                WarrantyOption.id == option_id,
                Product.tenant_id == tenant_id,
            )
        )
        return session.scalar(statement)

    def list_options(
        self,
        session: Session,
        tenant_id: int,
        offset: int,
        limit: int,
        product_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[WarrantyOption]:
        statement = (
            select(WarrantyOption)
            .join(Product, Product.id == WarrantyOption.product_id)
            .where(Product.tenant_id == tenant_id)
        )
        if product_id is not None:
            statement = statement.where(WarrantyOption.product_id == product_id)
        if is_active is not None:
            statement = statement.where(WarrantyOption.is_active.is_(is_active))
        statement = statement.order_by(WarrantyOption.id.desc()).offset(offset).limit(limit)
        return list(session.scalars(statement))

    def create_option(
        self, session: Session, option: WarrantyOption
    ) -> WarrantyOption:
        session.add(option)
        session.flush()
        return option

    def update_option(
        self, session: Session, option: WarrantyOption
    ) -> WarrantyOption:
        session.flush()
        return option

    def list_prices(
        self, session: Session, tenant_id: int, option_id: int
    ) -> list[WarrantyPrice]:
        statement = (
            select(WarrantyPrice)
            .join(WarrantyOption, WarrantyOption.id == WarrantyPrice.warranty_option_id)
            .join(Product, Product.id == WarrantyOption.product_id)
            .where(
                WarrantyPrice.warranty_option_id == option_id,
                Product.tenant_id == tenant_id,
            )
            .order_by(WarrantyPrice.valid_from.desc(), WarrantyPrice.id.desc())
        )
        return list(session.scalars(statement))

    def get_price(
        self, session: Session, tenant_id: int, price_id: int
    ) -> WarrantyPrice | None:
        statement = (
            select(WarrantyPrice)
            .join(WarrantyOption, WarrantyOption.id == WarrantyPrice.warranty_option_id)
            .join(Product, Product.id == WarrantyOption.product_id)
            .where(WarrantyPrice.id == price_id, Product.tenant_id == tenant_id)
        )
        return session.scalar(statement)

    def create_price(
        self, session: Session, price: WarrantyPrice
    ) -> WarrantyPrice:
        session.add(price)
        session.flush()
        return price

    def update_price(
        self, session: Session, price: WarrantyPrice
    ) -> WarrantyPrice:
        session.flush()
        return price