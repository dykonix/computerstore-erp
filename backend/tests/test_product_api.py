import unittest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.attribute import Attribute
from app.models.attribute_option import AttributeOption
from app.models.brand import Brand
from app.models.brand_category import BrandCategory
from app.models.category import Category
from app.models.category_attribute import CategoryAttribute
from app.models.product import Product
from app.models.product_attribute_value import ProductAttributeValue
from app.models.tenant import Tenant
from app.models.employee import Employee
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.api.routes.products import _product_response
from app.schemas.product import ProductAttributeValueCreate, ProductCreate
from app.services.product_service import ProductService, ProductValidationError


class FailingValueRepository:
    def __init__(self, delegate: ProductService) -> None:
        self.delegate = delegate

    def __getattr__(self, name):
        return getattr(self.delegate.repository, name)

    def add_attribute_value(self, session, value):
        raise RuntimeError("simulated attribute value failure")


class ProductServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with Session(self.engine) as session:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            tenant = Tenant(name="Tenant")
            category = Category(name="Laptop")
            second_category = Category(name="Desktop")
            active_brand = Brand(name="HP")
            second_brand = Brand(name="Lenovo")
            inactive_brand = Brand(name="Inactive", is_active=False)
            select_attribute = Attribute(name="RAM", data_type="SELECT")
            multi_attribute = Attribute(name="Connectors", data_type="MULTI_SELECT")
            number_attribute = Attribute(name="Weight", data_type="NUMBER")
            session.add_all(
                [
                    tenant,
                    category,
                    second_category,
                    active_brand,
                    second_brand,
                    inactive_brand,
                    select_attribute,
                    multi_attribute,
                    number_attribute,
                ]
            )
            session.flush()
            session.add_all(
                [
                    BrandCategory(
                        brand_id=active_brand.id, category_id=category.id
                    ),
                    BrandCategory(
                        brand_id=active_brand.id, category_id=second_category.id
                    ),
                    CategoryAttribute(
                        category_id=category.id,
                        attribute_id=select_attribute.id,
                        is_required=True,
                    ),
                    CategoryAttribute(
                        category_id=category.id,
                        attribute_id=number_attribute.id,
                    ),
                    CategoryAttribute(
                        category_id=category.id,
                        attribute_id=multi_attribute.id,
                    ),
                    CategoryAttribute(
                        category_id=second_category.id,
                        attribute_id=number_attribute.id,
                        is_required=True,
                    ),
                    AttributeOption(
                        attribute_id=select_attribute.id, value="16"
                    ),
                    AttributeOption(
                        attribute_id=multi_attribute.id, value="USB-A"
                    ),
                    AttributeOption(
                        attribute_id=multi_attribute.id, value="USB-C"
                    ),
                    AttributeOption(
                        attribute_id=multi_attribute.id, value="HDMI"
                    ),
                ]
            )
            session.commit()
            self.tenant_id = tenant.id
            self.category_id = category.id
            self.second_category_id = second_category.id
            self.brand_id = active_brand.id
            self.second_brand_id = second_brand.id
            self.inactive_brand_id = inactive_brand.id
            self.select_attribute_id = select_attribute.id
            self.number_attribute_id = number_attribute.id
            self.multi_attribute_id = multi_attribute.id
            self.option_id = session.scalar(
                select(AttributeOption.id).where(
                    AttributeOption.attribute_id == select_attribute.id
                )
            )
            self.multi_option_ids = list(
                session.scalars(
                    select(AttributeOption.id)
                    .where(AttributeOption.attribute_id == multi_attribute.id)
                    .order_by(AttributeOption.id)
                )
            )

    def request(self, **overrides):
        values = {
            "sku": "HP-ABC",
            "name": "HP OmniBook",
            "category_id": self.category_id,
            "brand_id": self.brand_id,
            "attributes": [
                ProductAttributeValueCreate(
                    attribute_id=self.select_attribute_id,
                    attribute_option_id=self.option_id,
                )
            ],
        }
        values.update(overrides)
        return ProductCreate(**values)

    def create(self, request=None, service=None):
        with Session(self.engine) as session:
            product = (service or ProductService()).create_product(
                session, self.tenant_id, request or self.request()
            )
            return product.id

    def update(self, product_id, request=None, service=None):
        with Session(self.engine) as session:
            product = (service or ProductService()).update_product(
                session, self.tenant_id, product_id, request or self.request()
            )
            return product.id

    def test_valid_product_creation(self):
        product_id = self.create()
        with Session(self.engine) as session:
            self.assertEqual(session.get(Product, product_id).name, "HP OmniBook")
            self.assertEqual(
                session.scalar(select(func.count()).select_from(ProductAttributeValue)),
                1,
            )

    def test_same_sku_is_allowed_for_second_configuration(self):
        self.create()
        second_id = self.create(
            self.request(name="HP OmniBook 16"),
        )
        self.assertIsNotNone(second_id)

    def test_invalid_category(self):
        with self.assertRaises(ProductValidationError):
            self.create(self.request(category_id=999))

    def test_invalid_or_inactive_brand(self):
        with self.assertRaises(ProductValidationError):
            self.create(self.request(brand_id=self.inactive_brand_id))

    def test_brand_not_associated_with_category(self):
        with self.assertRaises(ProductValidationError):
            self.create(self.request(brand_id=self.second_brand_id))

    def test_missing_required_attribute(self):
        with self.assertRaises(ProductValidationError):
            self.create(self.request(attributes=[]))

    def test_invalid_attribute_option(self):
        with self.assertRaises(ProductValidationError):
            self.create(
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=999,
                        )
                    ]
                )
            )

    def test_select_rejects_multiple_values(self):
        with self.assertRaises(ProductValidationError):
            self.create(
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=self.option_id,
                        ),
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=self.option_id,
                        ),
                    ]
                )
            )

    def test_multiselect_allows_multiple_distinct_options(self):
        product_id = self.create(
            self.request(
                attributes=[
                    ProductAttributeValueCreate(
                        attribute_id=self.select_attribute_id,
                        attribute_option_id=self.option_id,
                    ),
                    *[
                        ProductAttributeValueCreate(
                            attribute_id=self.multi_attribute_id,
                            attribute_option_id=option_id,
                        )
                        for option_id in self.multi_option_ids
                    ],
                ]
            )
        )
        with Session(self.engine) as session:
            values = session.scalars(
                select(ProductAttributeValue).where(
                    ProductAttributeValue.product_id == product_id,
                    ProductAttributeValue.attribute_id == self.multi_attribute_id,
                )
            ).all()
            self.assertEqual(
                {value.attribute_option_id for value in values},
                set(self.multi_option_ids),
            )

    def test_multiselect_rejects_duplicate_options(self):
        with self.assertRaises(ProductValidationError):
            self.create(
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=self.option_id,
                        ),
                        ProductAttributeValueCreate(
                            attribute_id=self.multi_attribute_id,
                            attribute_option_id=self.multi_option_ids[0],
                        ),
                        ProductAttributeValueCreate(
                            attribute_id=self.multi_attribute_id,
                            attribute_option_id=self.multi_option_ids[0],
                        ),
                    ]
                )
            )

    def test_product_response_returns_all_multiselect_options(self):
        product_id = self.create(
            self.request(
                attributes=[
                    ProductAttributeValueCreate(
                        attribute_id=self.select_attribute_id,
                        attribute_option_id=self.option_id,
                    ),
                    *[
                        ProductAttributeValueCreate(
                            attribute_id=self.multi_attribute_id,
                            attribute_option_id=option_id,
                        )
                        for option_id in self.multi_option_ids
                    ],
                ]
            )
        )
        with Session(self.engine) as session:
            row, values = ProductService().get_product(
                session, self.tenant_id, product_id
            )
            response = _product_response(row, values)
            selected = [
                item.attribute_option_value
                for item in response.attributes
                if item.attribute_id == self.multi_attribute_id
            ]
            self.assertEqual(selected, ["USB-A", "USB-C", "HDMI"])

    def test_wrong_value_type(self):
        with self.assertRaises(ProductValidationError):
            self.create(
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            text_value="16",
                        )
                    ]
                )
            )

    def test_tenant_id_is_rejected_from_request(self):
        with self.assertRaises(ValueError):
            ProductCreate(
                sku="HP-ABC",
                name="HP OmniBook",
                category_id=self.category_id,
                brand_id=self.brand_id,
                tenant_id=self.tenant_id,
            )

    def test_duplicate_attribute_in_request(self):
        with self.assertRaises(ProductValidationError):
            self.create(
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=self.option_id,
                        ),
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=self.option_id,
                        ),
                    ]
                )
            )

    def test_transaction_rolls_back_when_attribute_value_creation_fails(self):
        service = ProductService()
        service.repository = FailingValueRepository(service)
        with self.assertRaises(RuntimeError):
            self.create(service=service)
        with Session(self.engine) as session:
            self.assertEqual(
                session.scalar(select(func.count()).select_from(Product)), 0
            )

    def test_successful_update(self):
        product_id = self.create()
        self.update(product_id, self.request(name="Updated OmniBook"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(Product, product_id).name, "Updated OmniBook")

    def test_update_changes_sku(self):
        product_id = self.create()
        self.update(product_id, self.request(sku="HP-UPDATED"))
        with Session(self.engine) as session:
            self.assertEqual(session.get(Product, product_id).sku, "HP-UPDATED")

    def test_update_changes_attributes(self):
        product_id = self.create()
        request = self.request(
            attributes=[
                ProductAttributeValueCreate(
                    attribute_id=self.select_attribute_id,
                    attribute_option_id=self.option_id,
                ),
                ProductAttributeValueCreate(
                    attribute_id=self.number_attribute_id, number_value=42
                ),
            ]
        )
        self.update(product_id, request)
        with Session(self.engine) as session:
            value = session.scalar(
                select(ProductAttributeValue).where(
                    ProductAttributeValue.product_id == product_id,
                    ProductAttributeValue.attribute_id == self.number_attribute_id,
                )
            )
            self.assertEqual(value.number_value, 42)

    def test_update_changes_category_and_attributes(self):
        product_id = self.create()
        request = self.request(
            category_id=self.second_category_id,
            attributes=[
                ProductAttributeValueCreate(
                    attribute_id=self.number_attribute_id, number_value=64
                )
            ],
        )
        self.update(product_id, request)
        with Session(self.engine) as session:
            product = session.get(Product, product_id)
            values = session.scalars(
                select(ProductAttributeValue).where(
                    ProductAttributeValue.product_id == product_id
                )
            ).all()
            self.assertEqual(product.category_id, self.second_category_id)
            self.assertEqual(len(values), 1)
            self.assertEqual(values[0].attribute_id, self.number_attribute_id)

    def test_update_rejects_invalid_attribute_option(self):
        product_id = self.create()
        with self.assertRaises(ProductValidationError):
            self.update(
                product_id,
                self.request(
                    attributes=[
                        ProductAttributeValueCreate(
                            attribute_id=self.select_attribute_id,
                            attribute_option_id=999,
                        )
                    ]
                ),
            )

    def test_update_rejects_missing_required_attribute(self):
        product_id = self.create()
        with self.assertRaises(ProductValidationError):
            self.update(
                product_id,
                self.request(
                    category_id=self.second_category_id, attributes=[]
                ),
            )

    def test_update_rejects_invalid_product_id(self):
        with self.assertRaises(Exception) as context:
            self.update(999, self.request())
        self.assertEqual(type(context.exception).__name__, "ProductNotFoundError")

    def test_update_rolls_back_product_and_values_on_failure(self):
        product_id = self.create()
        service = ProductService()
        service.repository = FailingValueRepository(service)
        with self.assertRaises(RuntimeError):
            self.update(product_id, self.request(name="Should Roll Back"), service)
        with Session(self.engine) as session:
            product = session.get(Product, product_id)
            self.assertEqual(product.name, "HP OmniBook")
            self.assertEqual(
                session.scalar(select(func.count()).select_from(ProductAttributeValue).where(ProductAttributeValue.product_id == product_id)),
                1,
            )


if __name__ == "__main__":
    unittest.main()