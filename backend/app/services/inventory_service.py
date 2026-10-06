from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import InventoryTransferCreate, OpeningStockCreate


class InventoryNotFoundError(Exception):
    pass


class InventoryValidationError(Exception):
    pass


class InventoryService:
    def __init__(self, repository: InventoryRepository | None = None) -> None:
        self.repository = repository or InventoryRepository()

    def create_opening_stock(self, session: Session, tenant_id: int, request: OpeningStockCreate) -> Inventory:
        with session.begin():
            if (request.store_id is None) == (request.godown_id is None):
                raise InventoryValidationError("Exactly one of store_id or godown_id is required")
            product = self.repository.get_product(session, tenant_id, request.product_id)
            if product is None or not product.is_active:
                raise InventoryValidationError("Product does not exist or is inactive")
            supplier = self.repository.get_supplier(session, tenant_id, request.supplier_id)
            if supplier is None or not supplier.is_active:
                raise InventoryValidationError("Supplier does not exist, is inactive, or is outside the current tenant")
            if request.store_id is not None and self.repository.get_store(session, tenant_id, request.store_id) is None:
                raise InventoryValidationError("Store does not exist in the current tenant")
            if request.godown_id is not None and self.repository.get_godown(session, tenant_id, request.godown_id) is None:
                raise InventoryValidationError("Godown does not exist in the current tenant")
            if self.repository.get_inventory_at_location(session, tenant_id, request.product_id, request.store_id, request.godown_id) is not None:
                raise InventoryValidationError("Inventory balance already exists at this location")
            inventory = self.repository.add_inventory(session, Inventory(tenant_id=tenant_id, product_id=request.product_id, store_id=request.store_id, godown_id=request.godown_id, quantity=request.quantity, reserved_quantity=0))
            self.repository.add_movement(session, InventoryMovement(tenant_id=tenant_id, product_id=request.product_id, supplier_id=supplier.id, movement_type="OPENING", quantity=request.quantity, to_store_id=request.store_id, to_godown_id=request.godown_id))
            return inventory

    def transfer_inventory(
        self, session: Session, tenant_id: int, request: InventoryTransferCreate
    ) -> Inventory:
        with session.begin():
            if (request.source_store_id is None) == (request.source_godown_id is None):
                raise InventoryValidationError(
                    "Exactly one source store_id or godown_id is required"
                )
            if (request.destination_store_id is None) == (request.destination_godown_id is None):
                raise InventoryValidationError(
                    "Exactly one destination store_id or godown_id is required"
                )
            if (
                request.source_store_id is not None
                and request.source_store_id == request.destination_store_id
            ) or (
                request.source_godown_id is not None
                and request.source_godown_id == request.destination_godown_id
            ):
                raise InventoryValidationError(
                    "Source and destination locations must be different"
                )

            product = self.repository.get_product(session, tenant_id, request.product_id)
            if product is None or not product.is_active:
                raise InventoryValidationError("Product does not exist or is inactive")

            if request.source_store_id is not None:
                source_location = self.repository.get_store(
                    session, tenant_id, request.source_store_id
                )
            else:
                source_location = self.repository.get_godown(
                    session, tenant_id, request.source_godown_id
                )
            if source_location is None or not source_location.is_active:
                raise InventoryValidationError(
                    "Source location does not exist, is inactive, or is outside the current tenant"
                )

            if request.destination_store_id is not None:
                destination_location = self.repository.get_store(
                    session, tenant_id, request.destination_store_id
                )
            else:
                destination_location = self.repository.get_godown(
                    session, tenant_id, request.destination_godown_id
                )
            if destination_location is None or not destination_location.is_active:
                raise InventoryValidationError(
                    "Destination location does not exist, is inactive, or is outside the current tenant"
                )

            source = self.repository.get_inventory_at_location(
                session,
                tenant_id,
                request.product_id,
                request.source_store_id,
                request.source_godown_id,
                lock=True,
            )
            if source is None:
                raise InventoryValidationError("Source inventory balance does not exist")
            available_quantity = source.quantity - source.reserved_quantity
            if request.quantity > available_quantity:
                raise InventoryValidationError("Transfer quantity exceeds available stock")

            self.repository.adjust_inventory_quantity(
                session, tenant_id, source, -request.quantity
            )

            destination = self.repository.get_inventory_at_location(
                session,
                tenant_id,
                request.product_id,
                request.destination_store_id,
                request.destination_godown_id,
            )
            if destination is None:
                destination = self.repository.add_inventory(
                    session,
                    Inventory(
                        tenant_id=tenant_id,
                        product_id=request.product_id,
                        store_id=request.destination_store_id,
                        godown_id=request.destination_godown_id,
                        quantity=request.quantity,
                        reserved_quantity=0,
                    ),
                )
            else:
                self.repository.adjust_inventory_quantity(
                    session, tenant_id, destination, request.quantity
                )

            self.repository.add_movement(
                session,
                InventoryMovement(
                    tenant_id=tenant_id,
                    product_id=request.product_id,
                    movement_type="TRANSFER",
                    quantity=request.quantity,
                    from_store_id=request.source_store_id,
                    from_godown_id=request.source_godown_id,
                    to_store_id=request.destination_store_id,
                    to_godown_id=request.destination_godown_id,
                ),
            )
            return destination

    def get_inventory(self, session: Session, tenant_id: int, inventory_id: int):
        row = self.repository.get_inventory(session, tenant_id, inventory_id)
        if row is None:
            raise InventoryNotFoundError("Inventory record not found")
        return row

    def list_inventory(self, session: Session, tenant_id: int, page: int, page_size: int):
        return self.repository.list_inventory(session, tenant_id, (page - 1) * page_size, page_size), self.repository.count_inventory(session, tenant_id)