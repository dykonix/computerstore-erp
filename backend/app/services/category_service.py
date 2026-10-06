from sqlalchemy.orm import Session

from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryNotFoundError(Exception):
    pass


class CategoryValidationError(Exception):
    pass


class CategoryService:
    def __init__(self, repository: CategoryRepository | None = None):
        self.repository = repository or CategoryRepository()

    def create(
        self,
        session: Session,
        data: CategoryCreate,
    ) -> Category:
        name = data.name.strip()

        existing = self.repository.get_by_name(session, name)

        if existing:
            raise CategoryValidationError(
                "Category name already exists"
            )

        category = Category(
            name=name,
            description=data.description,
            gst_rate=data.gst_rate,
        )

        return self.repository.create(session, category)

    def get_by_id(
        self,
        session: Session,
        category_id: int,
    ) -> Category:
        category = self.repository.get_by_id(
            session,
            category_id,
        )

        if category is None:
            raise CategoryNotFoundError(
                "Category not found"
            )

        return category

    def list(
        self,
        session: Session,
        offset: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
    ) -> tuple[list[Category], int]:
        categories = self.repository.list(
            session,
            offset,
            limit,
            is_active,
        )

        total = self.repository.count(
            session,
            is_active,
        )

        return categories, total

    def update(
        self,
        session: Session,
        category_id: int,
        data: CategoryUpdate,
    ) -> Category:
        category = self.get_by_id(
            session,
            category_id,
        )

        if data.name is not None:
            new_name = data.name.strip()

            existing = self.repository.get_by_name(
                session,
                new_name,
            )

            if existing and existing.id != category.id:
                raise CategoryValidationError(
                    "Category name already exists"
                )

            category.name = new_name

        if data.description is not None:
            category.description = data.description

        if data.gst_rate is not None:
            category.gst_rate = data.gst_rate

        return self.repository.update(
            session,
            category,
        )

    def set_status(
        self,
        session: Session,
        category_id: int,
        is_active: bool,
    ) -> Category:
        category = self.get_by_id(
            session,
            category_id,
        )

        category.is_active = is_active

        return self.repository.update(
            session,
            category,
        )