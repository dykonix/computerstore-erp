"""merge sales employee nullable and user location assignments

Revision ID: fff2e3f86d85
Revises: 4f6c2a8b1d90, b6d4e81a2c90
Create Date: 2026-11-02 09:46:32.733656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fff2e3f86d85'
down_revision: Union[str, Sequence[str], None] = ('4f6c2a8b1d90', 'b6d4e81a2c90')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
