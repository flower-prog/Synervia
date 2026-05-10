"""add organization_id to conversations and rag_documents

Revision ID: 0005_org_tenant_isolation
Revises: 0004_audit_log
Create Date: 2026-05-10T21:25:26.101959+00:00

Adds optional organization_id FK (SET NULL on delete) to conversations and
rag_documents so every resource is scoped to one org context. Existing rows
are left NULL and will be backfilled by migration 0006.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0005_org_tenant_isolation"
down_revision = "0004_5_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])

    op.add_column(
        "rag_documents",
        sa.Column(
            "organization_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_rag_documents_organization_id", "rag_documents", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_column("conversations", "organization_id")

    op.drop_index("ix_rag_documents_organization_id", table_name="rag_documents")
    op.drop_column("rag_documents", "organization_id")
