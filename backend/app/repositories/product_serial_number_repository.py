from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_serial_number import ProductSerialNumber


class ProductSerialNumberRepository:
    def create(
        self,
        session: Session,
        serial_number: ProductSerialNumber,
    ) -> ProductSerialNumber:
        session.add(serial_number)
        session.flush()
        return serial_number

    def get_by_id(
        self,
        session: Session,
        tenant_id: int,
        serial_id: int,
        lock: bool = False,
    ) -> ProductSerialNumber | None:
        statement = select(ProductSerialNumber).where(
            ProductSerialNumber.id == serial_id,
            ProductSerialNumber.tenant_id == tenant_id,
        )

        if lock:
            statement = statement.with_for_update()

        return session.scalar(statement)

    def get_by_serial_number(
        self,
        session: Session,
        tenant_id: int,
        serial_number: str,
        lock: bool = False,
    ) -> ProductSerialNumber | None:
        statement = select(ProductSerialNumber).where(
            ProductSerialNumber.tenant_id == tenant_id,
            ProductSerialNumber.serial_number == serial_number,
        )

        if lock:
            statement = statement.with_for_update()

        return session.scalar(statement)

    def list_by_product(
        self,
        session: Session,
        tenant_id: int,
        product_id: int,
        status: str | None = None,
        lock: bool = False,
    ) -> list[ProductSerialNumber]:
        statement = (
            select(ProductSerialNumber)
            .where(
                ProductSerialNumber.tenant_id == tenant_id,
                ProductSerialNumber.product_id == product_id,
            )
            .order_by(ProductSerialNumber.id)
        )

        if status is not None:
            statement = statement.where(
                ProductSerialNumber.status == status
            )

        if lock:
            statement = statement.with_for_update()

        return list(session.scalars(statement))

    def update_status(
        self,
        session: Session,
        serial_number: ProductSerialNumber,
        status: str,
    ) -> ProductSerialNumber:
        serial_number.status = status
        session.flush()
        return serial_number