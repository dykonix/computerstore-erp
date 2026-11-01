"""merge tenant IAM and serial number migration heads

Revision ID: 3d23d9650f89
Revises: 9b3e5d7a1c42, d9a7c2f4e610
Create Date: 2026-11-01 14:25:42.644917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d23d9650f89'
down_revision: Union[str, Sequence[str], None] = ('9b3e5d7a1c42', 'd9a7c2f4e610')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
