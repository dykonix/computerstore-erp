from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.models.brand import Brand
from app.models.category import Category
from app.models.godown import Godown
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.product import Product
from app.models.store import Store
from app.models.supplier import Supplier


class InventoryRepository:
    def get_product(self, session: Session, tenant_id: int, product_id: int) -> Product | None:
        return session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )

    def get_store(self, session: Session, tenant_id: int, store_id: int) -> Store | None:
        return session.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.tenant_id == tenant_id,
            )
        )

    def get_godown(self, session: Session, tenant_id: int, godown_id: int) -> Godown | None:
        return session.scalar(
            select(Godown).where(
                Godown.id == godown_id,
                Godown.tenant_id == tenant_id,
            )
        )

    def get_supplier(self, session: Session, tenant_id: int, supplier_id: int) -> Supplier | None:
        return session.scalar(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.tenant_id == tenant_id,
            )
        )

    def get_inventory_at_location(
        self,
        session: Session,
        tenant_id: int,
        product_id: int,
        store_id: int | None,
        godown_id: int | None,
        lock: bool = False,
    ) -> Inventory | None:
        statement = select(Inventory).where(
            Inventory.tenant_id == tenant_id,
            Inventory.product_id == product_id,
        )

        statement = (
            statement.where(Inventory.store_id == store_id)
            if store_id is not None
            else statement.where(Inventory.godown_id == godown_id)
        )

        if lock:
            statement = statement.with_for_update()

        return session.scalar(statement)

    def add_inventory(self, session: Session, inventory: Inventory) -> Inventory:
        session.add(inventory)
        session.flush()
        return inventory

    def get_inventory_entity(
        self, session: Session, tenant_id: int, inventory_id: int
    ) -> Inventory | None:
        return session.scalar(
            select(Inventory).where(
                Inventory.id == inventory_id,
                Inventory.tenant_id == tenant_id,
            )
        )

    def update_inventory(self, session: Session, inventory: Inventory) -> Inventory:
        session.flush()
        return inventory

    def reserve_inventory(
        self,
        session: Session,
        tenant_id: int,
        inventory: Inventory,
        quantity: int,
    ) -> None:
        if quantity <= 0:
            raise ValueError("Reservation quantity must be greater than zero")

        available_quantity = inventory.quantity - inventory.reserved_quantity

        if available_quantity < quantity:
            raise ValueError("Insufficient available inventory")

        inventory.reserved_quantity += quantity
        session.flush()

    def adjust_inventory_quantity(
        self,
        session: Session,
        tenant_id: int,
        inventory: Inventory,
        quantity_delta: int,
    ) -> None:
        result = session.execute(
            update(Inventory)
            .where(
                Inventory.id == inventory.id,
                Inventory.tenant_id == tenant_id,
            )
            .values(quantity=Inventory.quantity + quantity_delta)
        )

        if result.rowcount != 1:
            raise RuntimeError("Inventory balance could not be updated")

        session.refresh(inventory, attribute_names=["quantity"])

    def add_movement(
        self,
        session: Session,
        movement: InventoryMovement,
    ) -> InventoryMovement:
        session.add(movement)
        session.flush()
        return movement

    def list_products(self, session: Session, tenant_id: int) -> list[Product]:
        return list(
            session.scalars(
                select(Product)
                .where(
                    Product.tenant_id == tenant_id,
                    Product.is_active.is_(True),
                )
                .order_by(Product.name, Product.id)
            )
        )

    def list_stores(self, session: Session, tenant_id: int) -> list[Store]:
        return list(
            session.scalars(
                select(Store)
                .where(
                    Store.tenant_id == tenant_id,
                    Store.is_active.is_(True),
                )
                .order_by(Store.name)
            )
        )

    def list_godowns(self, session: Session, tenant_id: int) -> list[Godown]:
        return list(
            session.scalars(
                select(Godown)
                .where(
                    Godown.tenant_id == tenant_id,
                    Godown.is_active.is_(True),
                )
                .order_by(Godown.name)
            )
        )

    def count_inventory(
        self,
        session: Session,
        tenant_id: int,
        product_id: int | None = None,
        store_id: int | None = None,
    ) -> int:
        filters = [Inventory.tenant_id == tenant_id]
        if product_id is not None:
            filters.append(Inventory.product_id == product_id)
        if store_id is not None:
            filters.append(Inventory.store_id == store_id)

        return (
            session.scalar(
                select(func.count())
                .select_from(Inventory)
                .where(*filters)
            )
            or 0
        )

    def list_inventory(
        self,
        session: Session,
        tenant_id: int,
        offset: int,
        limit: int,
        product_id: int | None = None,
        store_id: int | None = None,
    ):
        location_name = func.coalesce(Store.name, Godown.name)
        location_type = case(
            (Inventory.store_id.is_not(None), "Store"),
            else_="Godown",
        )

        filters = [Inventory.tenant_id == tenant_id]
        if product_id is not None:
            filters.append(Inventory.product_id == product_id)
        if store_id is not None:
            filters.append(Inventory.store_id == store_id)

        statement = (
            select(
                Inventory,
                Product.name,
                Product.sku,
                Brand.name,
                Category.name,
                location_type,
                location_name,
            )
            .join(Product, Product.id == Inventory.product_id)
            .join(Brand, Brand.id == Product.brand_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(Store, Store.id == Inventory.store_id)
            .outerjoin(Godown, Godown.id == Inventory.godown_id)
            .where(*filters)
            .order_by(Inventory.id.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(session.execute(statement).all())

    def get_inventory(
        self,
        session: Session,
        tenant_id: int,
        inventory_id: int,
    ):
        location_name = func.coalesce(Store.name, Godown.name)
        location_type = case(
            (Inventory.store_id.is_not(None), "Store"),
            else_="Godown",
        )

        statement = (
            select(
                Inventory,
                Product.name,
                Product.sku,
                Brand.name,
                Category.name,
                location_type,
                location_name,
            )
            .join(Product, Product.id == Inventory.product_id)
            .join(Brand, Brand.id == Product.brand_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(Store, Store.id == Inventory.store_id)
            .outerjoin(Godown, Godown.id == Inventory.godown_id)
            .where(
                Inventory.tenant_id == tenant_id,
                Inventory.id == inventory_id,
            )
        )

        return session.execute(statement).one_or_none()