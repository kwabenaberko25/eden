"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}
__eden_tenant_isolated__ = ${tenant_isolated if "tenant_isolated" in context.keys() else False}


def upgrade() -> None:
    from alembic import context
    is_tenant_context = context.config.get_main_option("tenant_schema") is not None
    if is_tenant_context != __eden_tenant_isolated__:
        # Skip this migration if the context doesn't match the migration type
        return

    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    from alembic import context
    is_tenant_context = context.config.get_main_option("tenant_schema") is not None
    if is_tenant_context != __eden_tenant_isolated__:
        return

    ${downgrades if downgrades else "pass"}


