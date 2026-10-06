from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_attribute_value import ProductAttributeValue
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductAttributeValueCreate, ProductCreate


class ProductNotFoundError(Exception):
    pass


class ProductValidationError(Exception):
    pass


class ProductService:
    def __init__(self, repository: ProductRepository | None = None) -> None:
        self.repository = repository or ProductRepository()

    def create_product(
        self, session: Session, tenant_id: int, request: ProductCreate
    ) -> Product:
        with session.begin():
            validated_values = self._validate_request(session, request)

            product = self.repository.add_product(
                session,
                Product(
                    tenant_id=tenant_id,
                    category_id=request.category_id,
                    brand_id=request.brand_id,
                    sku=request.sku,
                    name=request.name,
                    description=request.description,
                    is_active=request.is_active,
                ),
            )
            for item in validated_values:
                self.repository.add_attribute_value(
                    session,
                    ProductAttributeValue(
                        product_id=product.id,
                        attribute_id=item.attribute_id,
                        attribute_option_id=item.attribute_option_id,
                        text_value=item.text_value,
                        number_value=item.number_value,
                        decimal_value=item.decimal_value,
                    ),
                )
            return product

    def update_product(
        self,
        session: Session,
        tenant_id: int,
        product_id: int,
        request: ProductCreate,
    ) -> Product:
        with session.begin():
            product = self.repository.get_product_entity(session, tenant_id, product_id)
            if product is None:
                raise ProductNotFoundError("Product not found")

            validated_values = self._validate_request(session, request)
            product.category_id = request.category_id
            product.brand_id = request.brand_id
            product.sku = request.sku
            product.name = request.name
            product.description = request.description
            product.is_active = request.is_active
            self.repository.delete_product_attribute_values(session, product.id)
            for item in validated_values:
                self.repository.add_attribute_value(
                    session,
                    ProductAttributeValue(
                        product_id=product.id,
                        attribute_id=item.attribute_id,
                        attribute_option_id=item.attribute_option_id,
                        text_value=item.text_value,
                        number_value=item.number_value,
                        decimal_value=item.decimal_value,
                    ),
                )
            session.flush()
            return product

    def _validate_request(
        self, session: Session, request: ProductCreate
    ) -> list[ProductAttributeValueCreate]:
        category = self.repository.get_category(session, request.category_id)
        if category is None or not category.is_active:
            raise ProductValidationError("Category does not exist or is inactive")

        brand = self.repository.get_brand(session, request.brand_id)
        if brand is None or not brand.is_active:
            raise ProductValidationError("Brand does not exist or is inactive")
        if not self.repository.category_has_brand(
            session, request.category_id, request.brand_id
        ):
            raise ProductValidationError(
                "Brand is not associated with the selected category"
            )

        category_attributes = {
            item.attribute_id: item
            for item in self.repository.get_category_attributes_by_category(
                session, request.category_id
            )
        }
        supplied_ids = {item.attribute_id for item in request.attributes}
        missing_required = [
            attribute_id
            for attribute_id, relation in category_attributes.items()
            if relation.is_required and attribute_id not in supplied_ids
        ]
        if missing_required:
            raise ProductValidationError(
                "Required attributes are missing: "
                + ", ".join(str(item) for item in missing_required)
            )
        return self._validate_attribute_values(
            session, request.attributes, category_attributes.keys()
        )

    def _validate_attribute_values(
        self,
        session: Session,
        values: Iterable[ProductAttributeValueCreate],
        category_attribute_ids: Iterable[int],
    ) -> list[ProductAttributeValueCreate]:
        allowed_ids = set(category_attribute_ids)
        values_by_attribute: dict[int, list[ProductAttributeValueCreate]] = {}
        for item in values:
            values_by_attribute.setdefault(item.attribute_id, []).append(item)

        for attribute_id, items in values_by_attribute.items():
            attribute = self.repository.get_attribute(session, attribute_id)
            if attribute is None or not attribute.is_active:
                raise ProductValidationError(
                    f"Attribute {attribute_id} does not exist or is inactive"
                )
            if attribute_id not in allowed_ids:
                raise ProductValidationError(
                    f"Attribute {attribute_id} does not belong to the category"
                )
            if attribute.data_type == "SELECT" and len(items) != 1:
                raise ProductValidationError(
                    f"Attribute {attribute.name} accepts exactly one option"
                )
            if attribute.data_type != "MULTI_SELECT" and len(items) != 1:
                raise ProductValidationError(
                    f"Attribute {attribute.name} accepts only one value"
                )

            option_ids = [item.attribute_option_id for item in items]
            if attribute.data_type == "MULTI_SELECT" and len(option_ids) != len(set(option_ids)):
                raise ProductValidationError(
                    f"Duplicate options are not allowed for attribute {attribute.name}"
                )

        validated_values = []
        for item in values:
            if item.attribute_id not in allowed_ids:
                raise ProductValidationError(
                    f"Attribute {item.attribute_id} does not belong to the category"
                )
            attribute = self.repository.get_attribute(session, item.attribute_id)
            if attribute is None or not attribute.is_active:
                raise ProductValidationError(
                    f"Attribute {item.attribute_id} does not exist or is inactive"
                )

            fields = [
                item.attribute_option_id is not None,
                item.text_value is not None,
                item.number_value is not None,
                item.decimal_value is not None,
            ]
            if attribute.data_type in {"SELECT", "MULTI_SELECT"}:
                if item.attribute_option_id is None or sum(fields) != 1:
                    raise ProductValidationError(
                        f"Attribute {attribute.name} requires one valid option"
                    )
                option = self.repository.get_attribute_option(
                    session, item.attribute_option_id
                )
                if (
                    option is None
                    or not option.is_active
                    or option.attribute_id != attribute.id
                ):
                    raise ProductValidationError(
                        f"Invalid option for attribute {attribute.name}"
                    )
            elif attribute.data_type == "NUMBER":
                self._require_only(item, "number_value", attribute.name)
            elif attribute.data_type == "DECIMAL":
                self._require_only(item, "decimal_value", attribute.name)
            elif attribute.data_type == "TEXT":
                self._require_only(item, "text_value", attribute.name)
            else:
                raise ProductValidationError(
                    f"Unsupported attribute data type: {attribute.data_type}"
                )
            validated_values.append(item)
        return validated_values

    @staticmethod
    def _require_only(
        item: ProductAttributeValueCreate, field_name: str, attribute_name: str
    ) -> None:
        values = {
            "attribute_option_id": item.attribute_option_id,
            "text_value": item.text_value,
            "number_value": item.number_value,
            "decimal_value": item.decimal_value,
        }
        if values[field_name] is None or sum(value is not None for value in values.values()) != 1:
            raise ProductValidationError(
                f"Attribute {attribute_name} requires only {field_name}"
            )

    def list_products(
        self, session: Session, tenant_id: int, page: int, page_size: int
    ) -> tuple[list[tuple[Product, str, str]], int]:
        total = self.repository.count_products(session, tenant_id)
        rows = self.repository.list_products(
            session, tenant_id, (page - 1) * page_size, page_size
        )
        return rows, total

    def get_product(self, session: Session, tenant_id: int, product_id: int):
        product_row = self.repository.get_product(session, tenant_id, product_id)
        if product_row is None:
            raise ProductNotFoundError("Product not found")
        values = self.repository.get_product_attribute_values(session, product_id)
        return product_row, values