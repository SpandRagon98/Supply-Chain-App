"""Create backend foundation baseline.

Revision ID: 0001_backend_foundation
Revises:
Create Date: 2026-09-19
"""

from collections.abc import Sequence

revision: str = "0001_backend_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish the migration baseline before domain tables are introduced."""


def downgrade() -> None:
    """Remove the empty migration baseline."""
