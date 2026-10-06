from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.attribute import Attribute
from app.models.attribute_option import AttributeOption
from app.models.brand import Brand
from app.models.brand_category import BrandCategory
from app.models.category import Category
from app.models.category_attribute import CategoryAttribute
from app.models.product import Product
from app.models.product_attribute_value import ProductAttributeValue


class ProductRepository:
    def get_active_categories(self, session: Session) -> list[Category]:
        return list(
            session.scalars(
                select(Category)
                .where(Category.is_active.is_(True))
                .order_by(Category.name)
            )
        )

    def get_active_brands(self, session: Session) -> list[Brand]:
        return list(
            session.scalars(
                select(Brand).where(Brand.is_active.is_(True)).order_by(Brand.name)
            )
        )

    def get_active_attributes(self, session: Session) -> list[Attribute]:
        return list(
            session.scalars(
                select(Attribute)
                .where(Attribute.is_active.is_(True))
                .order_by(Attribute.name)
            )
        )

    def get_active_attribute_options(
        self, session: Session
    ) -> list[AttributeOption]:
        return list(
            session.scalars(
                select(AttributeOption)
                .where(AttributeOption.is_active.is_(True))
                .order_by(AttributeOption.attribute_id, AttributeOption.display_order)
            )
        )

    def get_category_attributes(
        self, session: Session
    ) -> list[CategoryAttribute]:
        return list(
            session.scalars(
                select(CategoryAttribute).order_by(
                    CategoryAttribute.category_id, CategoryAttribute.display_order
                )
            )
        )

    def get_category(self, session: Session, category_id: int) -> Category | None:
        return session.scalar(select(Category).where(Category.id == category_id))

    def get_brand(self, session: Session, brand_id: int) -> Brand | None:
        return session.scalar(select(Brand).where(Brand.id == brand_id))

    def get_attribute(self, session: Session, attribute_id: int) -> Attribute | None:
        return session.scalar(select(Attribute).where(Attribute.id == attribute_id))

    def get_attribute_option(
        self, session: Session, option_id: int
    ) -> AttributeOption | None:
        return session.scalar(
            select(AttributeOption).where(AttributeOption.id == option_id)
        )

    def category_has_brand(
        self, session: Session, category_id: int, brand_id: int
    ) -> bool:
        return (
            session.scalar(
                select(BrandCategory.brand_id).where(
                    BrandCategory.category_id == category_id,
                    BrandCategory.brand_id == brand_id,
                )
            )
            is not None
        )

    def get_category_attributes_by_category(
        self, session: Session, category_id: int
    ) -> list[CategoryAttribute]:
        return list(
            session.scalars(
                select(CategoryAttribute).where(
                    CategoryAttribute.category_id == category_id
                )
            )
        )

    def add_product(self, session: Session, product: Product) -> Product:
        session.add(product)
        session.flush()
        return product

    def add_attribute_value(
        self, session: Session, value: ProductAttributeValue
    ) -> ProductAttributeValue:
        session.add(value)
        session.flush()
        return value

    def get_product_entity(
        self, session: Session, tenant_id: int, product_id: int
    ) -> Product | None:
        return session.scalar(
            select(Product).where(
                Product.id == product_id, Product.tenant_id == tenant_id
            )
        )

    def delete_product_attribute_values(
        self, session: Session, product_id: int
    ) -> None:
        session.execute(
            delete(ProductAttributeValue).where(
                ProductAttributeValue.product_id == product_id
            )
        )

    def count_products(self, session: Session, tenant_id: int) -> int:
        return session.scalar(
            select(func.count()).select_from(Product).where(Product.tenant_id == tenant_id)
        ) or 0

    def list_products(
        self, session: Session, tenant_id: int, offset: int, limit: int
    ) -> list[tuple[Product, str, str]]:
        statement = (
            select(Product, Category.name, Brand.name)
            .join(Category, Category.id == Product.category_id)
            .join(Brand, Brand.id == Product.brand_id)
            .where(Product.tenant_id == tenant_id)
            .order_by(Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(session.execute(statement).all())

    def get_product(
        self, session: Session, tenant_id: int, product_id: int
    ) -> tuple[Product, str, str] | None:
        statement = (
            select(Product, Category.name, Brand.name)
            .join(Category, Category.id == Product.category_id)
            .join(Brand, Brand.id == Product.brand_id)
            .where(Product.tenant_id == tenant_id, Product.id == product_id)
        )
        return session.execute(statement).one_or_none()

    def get_product_attribute_values(
        self, session: Session, product_id: int
    ) -> list[tuple[ProductAttributeValue, Attribute, AttributeOption | None]]:
        statement = (
            select(ProductAttributeValue, Attribute, AttributeOption)
            .join(Attribute, Attribute.id == ProductAttributeValue.attribute_id)
            .outerjoin(
                AttributeOption,
                AttributeOption.id == ProductAttributeValue.attribute_option_id,
            )
            .where(ProductAttributeValue.product_id == product_id)
            .order_by(ProductAttributeValue.attribute_id)
        )
        return list(session.execute(statement).all())