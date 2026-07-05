"""gastos fijos

Revision ID: f3b8c1a9d4e6
Revises: c7a4e8f01d33
Create Date: 2026-07-04 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b8c1a9d4e6'
down_revision: Union[str, None] = 'c7a4e8f01d33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gastos_fijos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('concepto', sa.String(length=255), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('categoria', sa.String(length=50), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('id_usuario', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['id_usuario'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('gastos_fijos')
