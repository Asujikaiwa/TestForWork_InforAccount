"""Repayments between members.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("from_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("to_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("from_user_id <> to_user_id", name="ck_payments_not_to_self"),
        sa.UniqueConstraint(
            "group_id", "idempotency_key", name="uq_payments_group_idempotency_key"
        ),
    )
    op.create_index("ix_payments_group_id", "payments", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_group_id", table_name="payments")
    op.drop_table("payments")
