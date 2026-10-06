from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.warranty_option import WarrantyOption
from app.models.warranty_price import WarrantyPrice
from app.repositories.warranty_repository import WarrantyRepository
from app.schemas.warranty import (
    WarrantyOptionCreate,
    WarrantyOptionUpdate,
    WarrantyPriceCreate,
    WarrantyPriceUpdate,
)


class WarrantyNotFoundError(Exception):
    pass


class WarrantyValidationError(Exception):
    pass


class WarrantyService:
    def __init__(self, repository: WarrantyRepository | None = None) -> None:
        self.repository = repository or WarrantyRepository()

    def list_options(
        self,
        session: Session,
        tenant_id: int,
        page: int,
        page_size: int,
        product_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[WarrantyOption]:
        return self.repository.list_options(
            session,
            tenant_id,
            (page - 1) * page_size,
            page_size,
            product_id,
            is_active,
        )

    def get_option(
        self, session: Session, tenant_id: int, option_id: int
    ) -> WarrantyOption:
        option = self.repository.get_option(session, tenant_id, option_id)
        if option is None:
            raise WarrantyNotFoundError("Warranty option not found")
        return option

    def create_option(
        self,
        session: Session,
        tenant_id: int,
        request: WarrantyOptionCreate,
    ) -> WarrantyOption:
        with session.begin():
            product = self.repository.get_product(
                session, tenant_id, request.product_id
            )
            if product is None:
                raise WarrantyValidationError(
                    "Product does not exist in the current tenant"
                )
            return self.repository.create_option(
                session,
                WarrantyOption(
                    product_id=product.id,
                    additional_months=request.additional_months,
                    is_active=True,
                ),
            )

    def update_option(
        self,
        session: Session,
        tenant_id: int,
        option_id: int,
        request: WarrantyOptionUpdate,
    ) -> WarrantyOption:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise WarrantyValidationError("At least one field must be provided")
        if "additional_months" in updates and (
            updates["additional_months"] is None
            or updates["additional_months"] <= 0
        ):
            raise WarrantyValidationError("additional_months must be greater than 0")

        with session.begin():
            option = self.repository.get_option(session, tenant_id, option_id)
            if option is None:
                raise WarrantyNotFoundError("Warranty option not found")
            for field, value in updates.items():
                setattr(option, field, value)
            return self.repository.update_option(session, option)

    def set_option_status(
        self,
        session: Session,
        tenant_id: int,
        option_id: int,
        is_active: bool,
    ) -> WarrantyOption:
        with session.begin():
            option = self.repository.get_option(session, tenant_id, option_id)
            if option is None:
                raise WarrantyNotFoundError("Warranty option not found")
            option.is_active = is_active
            return self.repository.update_option(session, option)

    def list_prices(
        self, session: Session, tenant_id: int, option_id: int
    ) -> list[WarrantyPrice]:
        self.get_option(session, tenant_id, option_id)
        return self.repository.list_prices(session, tenant_id, option_id)

    def create_price(
        self,
        session: Session,
        tenant_id: int,
        option_id: int,
        request: WarrantyPriceCreate,
    ) -> WarrantyPrice:
        self._validate_price(request.price, request.valid_from, request.valid_to)
        with session.begin():
            option = self.repository.get_option(session, tenant_id, option_id)
            if option is None:
                raise WarrantyValidationError(
                    "Warranty option does not exist in the current tenant"
                )
            return self.repository.create_price(
                session,
                WarrantyPrice(
                    warranty_option_id=option.id,
                    price=request.price,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                ),
            )

    def update_price(
        self,
        session: Session,
        tenant_id: int,
        price_id: int,
        request: WarrantyPriceUpdate,
    ) -> WarrantyPrice:
        updates = request.model_dump(exclude_unset=True)
        if not updates:
            raise WarrantyValidationError("At least one field must be provided")
        if "price" in updates and updates["price"] is None:
            raise WarrantyValidationError("price cannot be empty")
        if "valid_from" in updates and updates["valid_from"] is None:
            raise WarrantyValidationError("valid_from cannot be empty")

        with session.begin():
            price = self.repository.get_price(session, tenant_id, price_id)
            if price is None:
                raise WarrantyNotFoundError("Warranty price not found")

            effective_price = updates.get("price", price.price)
            effective_valid_from = updates.get("valid_from", price.valid_from)
            effective_valid_to = updates.get("valid_to", price.valid_to)
            self._validate_price(
                effective_price, effective_valid_from, effective_valid_to
            )

            for field, value in updates.items():
                setattr(price, field, value)
            return self.repository.update_price(session, price)

    @staticmethod
    def _validate_price(
        price: Decimal, valid_from: date, valid_to: date | None
    ) -> None:
        if price < 0:
            raise WarrantyValidationError("price cannot be negative")
        if valid_to is not None and valid_to < valid_from:
            raise WarrantyValidationError(
                "valid_to cannot be earlier than valid_from"
            )