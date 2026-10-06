"""Seed the initial global product configuration.

Run with: ``cd backend && python -m app.seed``
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.attribute import Attribute
from app.models.attribute_option import AttributeOption
from app.models.brand import Brand
from app.models.brand_category import BrandCategory
from app.models.category import Category
from app.models.category_attribute import CategoryAttribute
from app.models.employee import Employee
from app.models.godown import Godown
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.store import Store
from app.models.tenant import Tenant

load_dotenv()

CATEGORY_NAMES = [
    "Laptop",
    "Desktop",
    "All-in-One",
    "Headphones",
    "Tablets",
    "Hard Disk",
]

BRAND_NAMES = [
    "HP",
    "Lenovo",
    "Dell",
    "ASUS",
    "Acer",
    "Apple",
    "Samsung",
    "Seagate",
    "Western Digital",
    "Sony",
    "JBL",
]

BRAND_CATEGORIES = {
    "HP": ["Laptop", "Desktop", "All-in-One", "Headphones", "Tablets"],
    "Lenovo": ["Laptop", "Desktop", "All-in-One", "Tablets"],
    "Dell": ["Laptop", "Desktop", "All-in-One"],
    "ASUS": ["Laptop", "Desktop", "All-in-One", "Headphones", "Tablets"],
    "Acer": ["Laptop", "Desktop", "All-in-One"],
    "Apple": ["Laptop", "Desktop", "All-in-One", "Tablets"],
    "Samsung": ["Tablets", "Headphones", "Hard Disk"],
    "Seagate": ["Hard Disk"],
    "Western Digital": ["Hard Disk"],
    "Sony": ["Headphones", "Tablets"],
    "JBL": ["Headphones"],
}

ATTRIBUTE_DEFINITIONS = {
    "RAM": ("SELECT", "GB"),
    "Processor": ("SELECT", None),
    "Screen Size": ("SELECT", "inch"),
    "Storage": ("SELECT", "GB"),
    "Storage Type": ("SELECT", None),
    "Graphics": ("SELECT", None),
    "Operating System": ("SELECT", None),
    "Color": ("SELECT", None),
    "Warranty": ("SELECT", "year"),
    "Connectors": ("MULTI_SELECT", None),
}

ATTRIBUTE_OPTIONS = {
    "RAM": ["4", "8", "16", "32", "64"],
    "Processor": [
        "Intel Core i3",
        "Intel Core i5",
        "Intel Core i7",
        "Intel Core i9",
        "Intel Core Ultra 5",
        "Intel Core Ultra 7",
        "Intel Core Ultra 9",
        "AMD Ryzen 3",
        "AMD Ryzen 5",
        "AMD Ryzen 7",
        "AMD Ryzen 9",
        "Apple M1",
        "Apple M2",
        "Apple M3",
        "Apple M4",
    ],
    "Screen Size": ["11", "12.4", "13.3", "13.6", "14", "15.6", "16", "17.3"],
    "Storage": ["128", "256", "512", "1024", "2048", "4096"],
    "Storage Type": ["HDD", "SSD", "NVMe"],
    "Graphics": [
        "Integrated",
        "Intel UHD",
        "Intel Iris Xe",
        "Intel Arc",
        "NVIDIA GeForce RTX 2050",
        "NVIDIA GeForce RTX 3050",
        "NVIDIA GeForce RTX 4050",
        "NVIDIA GeForce RTX 4060",
        "NVIDIA GeForce RTX 4070",
        "AMD Radeon",
    ],
    "Operating System": [
        "Windows 11 Home",
        "Windows 11 Pro",
        "Ubuntu",
        "FreeDOS",
        "macOS",
        "Android",
    ],
    "Color": ["Black", "Silver", "Grey", "White", "Blue", "Gold"],
    "Warranty": ["1", "2", "3"],
    "Connectors": [
        "USB-A",
        "USB-C",
        "HDMI",
        "DisplayPort",
        "Ethernet",
        "3.5mm Audio",
        "Thunderbolt",
    ],
}

CATEGORY_ATTRIBUTES = {
    "Laptop": [
        "RAM",
        "Processor",
        "Screen Size",
        "Storage",
        "Storage Type",
        "Graphics",
        "Operating System",
        "Color",
        "Warranty",
        "Connectors",
    ],
    "Desktop": [
        "RAM",
        "Processor",
        "Storage",
        "Storage Type",
        "Graphics",
        "Operating System",
        "Color",
        "Warranty",
        "Connectors",
    ],
    "All-in-One": [
        "RAM",
        "Processor",
        "Screen Size",
        "Storage",
        "Storage Type",
        "Graphics",
        "Operating System",
        "Color",
        "Warranty",
        "Connectors",
    ],
    "Headphones": ["Storage", "Color", "Warranty", "Connectors"],
    "Tablets": [
        "RAM",
        "Processor",
        "Screen Size",
        "Storage",
        "Operating System",
        "Color",
        "Warranty",
        "Connectors",
    ],
    "Hard Disk": ["Storage", "Storage Type", "Color", "Warranty", "Connectors"],
}

TENANT_NAME = "Mahamaya Computers"
STORE_NAMES = ["Mahamaya Computers", "HP World SBP", "HP World JSG"]
GODOWN_NAMES = ["Budharaja"]
ROLE_NAME = "Admin"
PERMISSION_CODE = "ALL"
SELL_PERMISSION_CODE = "sell"
SALES_ROLE_NAME = "Sales"
SALES_GLOBAL_ROLE_NAME = "Sales Global"
EMPLOYEE_EMAIL = "dykonix@gmail.com"
EMPLOYEE_NAME = "Dykonix"


def get_or_create_category(session: Session, name: str) -> Category:
    category = session.scalar(select(Category).where(Category.name == name))
    if category is None:
        category = Category(name=name)
        session.add(category)
    return category


def get_or_create_brand(session: Session, name: str) -> Brand:
    brand = session.scalar(select(Brand).where(Brand.name == name))
    if brand is None:
        brand = Brand(name=name)
        session.add(brand)
    return brand


def get_or_create_attribute(
    session: Session, name: str, data_type: str, unit: str | None
) -> Attribute:
    attribute = session.scalar(select(Attribute).where(Attribute.name == name))
    if attribute is None:
        attribute = Attribute(name=name, data_type=data_type, unit=unit)
        session.add(attribute)
    return attribute


def get_or_create_tenant(session: Session, name: str) -> Tenant:
    tenant = session.scalar(select(Tenant).where(Tenant.name == name))
    if tenant is None:
        tenant = Tenant(name=name)
        session.add(tenant)
    return tenant


def get_or_create_store(session: Session, tenant_id: int, name: str) -> Store:
    store = session.scalar(
        select(Store).where(Store.tenant_id == tenant_id, Store.name == name)
    )
    if store is None:
        store = Store(tenant_id=tenant_id, name=name)
        session.add(store)
    return store


def get_or_create_godown(session: Session, tenant_id: int, name: str) -> Godown:
    godown = session.scalar(
        select(Godown).where(Godown.tenant_id == tenant_id, Godown.name == name)
    )
    if godown is None:
        godown = Godown(tenant_id=tenant_id, name=name)
        session.add(godown)
    return godown


def get_or_create_role(session: Session, tenant_id: int, name: str) -> Role:
    role = session.scalar(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )
    if role is None:
        role = Role(tenant_id=tenant_id, name=name)
        session.add(role)
    return role


def get_or_create_permission(session: Session, code: str) -> Permission:
    permission = session.scalar(select(Permission).where(Permission.code == code))
    if permission is None:
        permission = Permission(code=code)
        session.add(permission)
    return permission


def set_role_permission_scope(
    session: Session, role: Role, permission: Permission, scope: str
) -> None:
    grant_key = (role.id, permission.id)
    grant = session.get(RolePermission, grant_key)
    if grant is None:
        session.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                scope=scope,
            )
        )
    elif grant.scope != scope:
        grant.scope = scope


def seed_authorization(session: Session, tenant_id: int) -> None:
    """Seed V1 authorization configuration for one existing tenant."""
    admin_role = get_or_create_role(session, tenant_id, ROLE_NAME)
    sales_role = get_or_create_role(session, tenant_id, SALES_ROLE_NAME)
    sales_global_role = get_or_create_role(
        session, tenant_id, SALES_GLOBAL_ROLE_NAME
    )
    all_permission = get_or_create_permission(session, PERMISSION_CODE)
    sell_permission = get_or_create_permission(session, SELL_PERMISSION_CODE)
    session.flush()

    set_role_permission_scope(
        session, admin_role, all_permission, "assigned_stores"
    )
    set_role_permission_scope(
        session, sales_role, sell_permission, "assigned_stores"
    )
    set_role_permission_scope(
        session, sales_global_role, sell_permission, "all_tenant_stores"
    )


def get_or_create_employee(
    session: Session, tenant_id: int, email: str, name: str
) -> Employee:
    employee = session.scalar(
        select(Employee).where(
            Employee.tenant_id == tenant_id, Employee.email == email
        )
    )
    if employee is None:
        employee = Employee(tenant_id=tenant_id, email=email, name=name)
        session.add(employee)
    return employee


def seed_attribute_options(
    session: Session, attributes: dict[str, Attribute]
) -> None:
    for attribute_name, option_values in ATTRIBUTE_OPTIONS.items():
        attribute = attributes[attribute_name]
        for display_order, value in enumerate(option_values):
            option = session.scalar(
                select(AttributeOption).where(
                    AttributeOption.attribute_id == attribute.id,
                    AttributeOption.value == value,
                )
            )
            if option is None:
                session.add(
                    AttributeOption(
                        attribute_id=attribute.id,
                        value=value,
                        display_order=display_order,
                    )
                )


def seed() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        categories = {
            name: get_or_create_category(session, name) for name in CATEGORY_NAMES
        }
        brands = {name: get_or_create_brand(session, name) for name in BRAND_NAMES}
        attributes = {
            name: get_or_create_attribute(session, name, data_type, unit)
            for name, (data_type, unit) in ATTRIBUTE_DEFINITIONS.items()
        }
        tenant = get_or_create_tenant(session, TENANT_NAME)
        session.flush()
        stores = {
            name: get_or_create_store(session, tenant.id, name) for name in STORE_NAMES
        }
        godowns = {
            name: get_or_create_godown(session, tenant.id, name)
            for name in GODOWN_NAMES
        }
        seed_authorization(session, tenant.id)
        employee = get_or_create_employee(
            session, tenant.id, EMPLOYEE_EMAIL, EMPLOYEE_NAME
        )
        session.flush()
        seed_attribute_options(session, attributes)

        for brand_name, category_names in BRAND_CATEGORIES.items():
            for category_name in category_names:
                association_key = (brands[brand_name].id, categories[category_name].id)
                if session.get(BrandCategory, association_key) is None:
                    session.add(
                        BrandCategory(
                            brand_id=association_key[0],
                            category_id=association_key[1],
                        )
                    )

        for category_name, attribute_names in CATEGORY_ATTRIBUTES.items():
            for display_order, attribute_name in enumerate(attribute_names):
                association_key = (
                    categories[category_name].id,
                    attributes[attribute_name].id,
                )
                if session.get(CategoryAttribute, association_key) is None:
                    session.add(
                        CategoryAttribute(
                            category_id=association_key[0],
                            attribute_id=association_key[1],
                            display_order=display_order,
                        )
                    )

    engine.dispose()
    print("Global and tenant configuration seeded successfully.")


if __name__ == "__main__":
    seed()