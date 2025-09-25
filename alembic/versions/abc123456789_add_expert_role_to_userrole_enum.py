"""add_expert_role_to_userrole_enum

Revision ID: abc123456789
Revises: 97ba1b9d601b
Create Date: 2025-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abc123456789'
down_revision = '97ba1b9d601b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add EXPERT to the userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE 'EXPERT'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type and updating all references
    pass