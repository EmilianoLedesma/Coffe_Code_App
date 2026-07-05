"""revertir soft delete recetas

Revision ID: c7a4e8f01d33
Revises: a1f9c3d7e5b2
Create Date: 2026-07-04 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a4e8f01d33'
down_revision: Union[str, None] = 'a1f9c3d7e5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Las filas ya marcadas como inactivas representan recetas que un usuario
    # eliminó intencionalmente; hay que borrarlas de verdad antes de quitar la
    # columna, o "revivirían" como activas al perder el flag.
    op.execute("DELETE FROM recetas WHERE activo = false")
    op.drop_column('recetas', 'activo')


def downgrade() -> None:
    op.add_column(
        'recetas',
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
