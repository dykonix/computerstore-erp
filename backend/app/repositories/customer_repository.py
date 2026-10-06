from sqlalchemy import select
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