"""add outbox routing_key

Revision ID: c3d2e1f0a9b8
Revises: af4ff5e9a708
Create Date: 2026-10-08 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d2e1f0a9b8'
down_revision: Union[str, Sequence[str], None] = 'af4ff5e9a708'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'outbox', sa.Column('routing_key', sa.String(length=255), nullable=True)
    )
    # Существующие строки созданы до relay и все относятся к payment.new
    op.execute("UPDATE outbox SET routing_key = 'payments.new'")
    op.alter_column(
        'outbox', 'routing_key', existing_type=sa.String(length=255), nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outbox', 'routing_key')
