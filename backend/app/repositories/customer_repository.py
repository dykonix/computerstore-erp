from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer


class CustomerRepository:
    def get_customer(
        self,
        session: Session,
        tenant_id: int,
        customer_id: int,
    ) -> Customer | None:
        return session.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.tenant_id == tenant_id,
            )
        )

    def list_active_customers(
        self,
        session: Session,
        tenant_id: int,
    ) -> list[Customer]:
        statement = (
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.is_active.is_(True),
            )
            .order_by(Customer.name.asc())
        )

        return list(session.scalars(statement).all())

    def search_customers(
        self,
        session: Session,
        tenant_id: int,
        query: str,
    ) -> list[Customer]:
        term = (query or '').strip()

        if not term:
            return []

        search_value = f'%{term.lower()}%'

        statement = (
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.is_active.is_(True),
                or_(
                    func.lower(Customer.name).like(search_value),
                    func.lower(Customer.mobile).like(search_value),
                ),
            )
            .order_by(Customer.name.asc())
        )

        return list(session.scalars(statement).all())

    def create_customer(
        self,
        session: Session,
        tenant_id: int,
        name: str,
        mobile: str,
        email: str | None = None,
        address: str | None = None,
    ) -> Customer:
        customer = Customer(
            tenant_id=tenant_id,
            name=name.strip(),
            mobile=mobile.strip(),
            email=email.strip() if email else None,
            address=address.strip() if address else None,
            is_active=True,
        )

        session.add(customer)
        session.flush()
        return customer

    def get_customer_by_mobile(
        self,
        session: Session,
        tenant_id: int,
        mobile: str,
    ) -> Customer | None:
        return session.scalar(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                func.lower(Customer.mobile) == mobile.strip().lower(),
            )
        )
