from sqlalchemy.orm import Session

from app.repositories.customer_repository import CustomerRepository


class CustomerService:
    def __init__(self) -> None:
        self.customer_repository = CustomerRepository()

    def list_active_customers(
        self,
        session: Session,
        tenant_id: int,
    ):
        return self.customer_repository.list_active_customers(
            session,
            tenant_id,
        )

    def search_customers(
        self,
        session: Session,
        tenant_id: int,
        query: str,
    ):
        return self.customer_repository.search_customers(
            session,
            tenant_id,
            query,
        )

    def create_customer(
        self,
        session: Session,
        tenant_id: int,
        name: str,
        mobile: str,
        email: str | None = None,
        address: str | None = None,
    ):
        trimmed_name = (name or '').strip()
        trimmed_mobile = (mobile or '').strip()

        if not trimmed_name:
            raise ValueError('Customer name is required')

        if not trimmed_mobile:
            raise ValueError('Customer mobile is required')

        existing_customer = self.customer_repository.get_customer_by_mobile(
            session,
            tenant_id,
            trimmed_mobile,
        )

        if existing_customer is not None:
            raise ValueError(
                'A customer with this mobile number already exists for this tenant'
            )

        return self.customer_repository.create_customer(
            session,
            tenant_id,
            trimmed_name,
            trimmed_mobile,
            email,
            address,
        )