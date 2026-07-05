"""soft delete recetas

Revision ID: a1f9c3d7e5b2
Revises: 2e2aaac64acf
Create Date: 2026-07-04 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f9c3d7e5b2'
down_revision: Union[str, None] = '2e2aaac64acf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'recetas',
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )


def downgrade() -> None:
    op.drop_column('recetas', 'activo')
