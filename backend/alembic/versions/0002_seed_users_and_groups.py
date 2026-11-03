"""Seed data from the brief: four users and two groups.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

USERS = [(1, "alice"), (2, "bob"), (3, "carol"), (4, "dan")]
GROUPS = [(1, "Chiang Mai trip"), (2, "Office lunch")]
# (group_id, user_id, position)
MEMBERS = [(1, 1, 0), (1, 2, 1), (1, 3, 2), (2, 2, 0), (2, 4, 1)]

users = sa.table("users", sa.column("id"), sa.column("username"))
groups = sa.table("groups", sa.column("id"), sa.column("name"))
members = sa.table(
    "group_members", sa.column("group_id"), sa.column("user_id"), sa.column("position")
)


def upgrade() -> None:
    op.bulk_insert(users, [{"id": i, "username": u} for i, u in USERS])
    op.bulk_insert(groups, [{"id": i, "name": n} for i, n in GROUPS])
    op.bulk_insert(members, [{"group_id": g, "user_id": u, "position": p} for g, u, p in MEMBERS])
    # Explicit ids were inserted, so move the sequences past them.
    op.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
    op.execute("SELECT setval('groups_id_seq', (SELECT MAX(id) FROM groups))")


def downgrade() -> None:
    op.execute("DELETE FROM group_members WHERE group_id IN (1, 2)")
    op.execute("DELETE FROM groups WHERE id IN (1, 2)")
    op.execute("DELETE FROM users WHERE id IN (1, 2, 3, 4)")
