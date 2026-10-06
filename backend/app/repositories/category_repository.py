from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    def create(self, session: Session, category: Category) -> Category:
        session.add(category)
        session.flush()
        return category

    def get_by_id(
        self, session: Session, category_id: int
    ) -> Category | None:
        return session.scalar(
            select(Category).where(Category.id == category_id)
        )

    def get_by_name(
        self, session: Session, name: str
    ) -> Category | None:
        return session.scalar(
            select(Category).where(Category.name == name)
        )

    def count(
        self, session: Session, is_active: bool | None = None
    ) -> int:
        statement = select(func.count()).select_from(Category)

        if is_active is not None:
            statement = statement.where(
                Category.is_active.is_(is_active)
            )

        return session.scalar(statement) or 0

    def list(
        self,
        session: Session,
        offset: int,
        limit: int,
        is_active: bool | None = None,
    ) -> list[Category]:
        statement = select(Category)

        if is_active is not None:
            statement = statement.where(
                Category.is_active.is_(is_active)
            )

        statement = (
            statement
            .order_by(Category.id.desc())
            .offset(offset)
            .limit(limit)
        )

        return list(session.scalars(statement))

    def update(
        self, session: Session, category: Category
    ) -> Category:
        session.flush()
        return category