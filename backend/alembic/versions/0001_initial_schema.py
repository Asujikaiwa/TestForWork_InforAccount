"""Initial schema: users, groups, members, expenses, expense shares.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
    )
    op.create_table(
        "group_members",
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False),
    )
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("paid_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("split_type", sa.String(10), nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.CheckConstraint("split_type IN ('equal', 'exact')", name="ck_expenses_split_type"),
        sa.UniqueConstraint(
            "group_id", "idempotency_key", name="uq_expenses_group_idempotency_key"
        ),
    )
    op.create_index("ix_expenses_group_id", "expenses", ["group_id"])
    op.create_table(
        "expense_shares",
        sa.Column("expense_id", sa.Integer, sa.ForeignKey("expenses.id"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_expense_shares_amount"),
    )


def downgrade() -> None:
    op.drop_table("expense_shares")
    op.drop_index("ix_expenses_group_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")
