"""
Eden — Authentication CLI Commands

Provides CLI commands for managing authentication:
    eden auth createsuperuser  — Create a new superuser account
    eden auth changepassword   — Change password for an admin or superuser
"""

import asyncio

import click

from eden.auth.models import User
from eden.db import Database


@click.group()
def auth():
    """Authentication and Authorization management."""
    pass


@auth.command()
@click.option("--email", prompt="Email address", help="The email for the superuser.")
@click.option("--full-name", prompt="Full name", help="The full name for the superuser.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="The password for the superuser.")
def createsuperuser(email, full_name, password):
    """Create a superuser with administrative privileges."""

    async def _create():
        from eden.config import get_config
        config = get_config()
        db = Database(config.get_database_url())
        await db.connect()

        async with db.transaction() as session:
            try:
                # Check if user exists
                existing = await User.query(session).filter(email=email).first()
                if existing:
                    click.echo(f"Error: User with email {email} already exists.")
                    return

                user = User(
                    email=email,
                    full_name=full_name,
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                    roles_json=["admin"],
                    permissions_json=["*"]
                )
                user.set_password(password)
                await user.save(session)
                click.echo(f"Successfully created superuser: {email}")

            except Exception as e:
                click.echo(f"Error creating superuser: {e}")

    asyncio.run(_create())


@auth.command()
@click.option("--email", default=None, help="Look up the user by email address.")
@click.option("--username", default=None, help="Look up the user by full name (username).")
@click.option(
    "--tenant", default=None,
    help="Tenant slug — scope the lookup to a specific tenant (schema-based or row-level).",
)
@click.option(
    "--password", prompt=True, hide_input=True, confirmation_prompt=True,
    help="The new password.",
)
def changepassword(email, username, tenant, password):
    """Change the password for an admin or superuser account.

    Looks up the target user by --email or --username (full name).
    When multi-tenancy is enabled, use --tenant <slug> to scope the
    lookup to that tenant's schema or row-level partition.

    \b
    Examples:
        eden auth changepassword --email admin@example.com
        eden auth changepassword --username "Jane Doe"
        eden auth changepassword --email admin@acme.com --tenant acme-corp
    """
    if not email and not username:
        email = click.prompt("Email address or username")
        # If it looks like an email, treat it as one; otherwise use as username
        if "@" in email:
            username = None
        else:
            username = email
            email = None

    async def _change():
        from sqlalchemy import select, or_, text
        from eden.config import get_config

        config = get_config()
        db = Database(config.get_database_url())
        await db.connect()

        async with db.transaction() as session:
            try:
                # ── Tenant scoping ──────────────────────────────────────
                tenant_obj = None
                original_search_path = None

                if tenant:
                    try:
                        from eden.tenancy.models import Tenant

                        tenant_result = await session.execute(
                            select(Tenant).where(Tenant.slug == tenant)
                        )
                        tenant_obj = tenant_result.scalar_one_or_none()

                        if not tenant_obj:
                            click.secho(
                                f"  ❌ Error: Tenant with slug '{tenant}' not found.",
                                fg="red", err=True,
                            )
                            return

                        # Schema-based tenancy: switch search_path
                        if tenant_obj.schema_name:
                            result = await session.execute(text("SHOW search_path"))
                            original_search_path = result.scalar()
                            await session.execute(
                                text(f"SET search_path TO {tenant_obj.schema_name}, public")
                            )
                            click.echo(
                                f"  🏢 Scoped to tenant '{tenant_obj.name}' "
                                f"(schema: {tenant_obj.schema_name})"
                            )
                        else:
                            click.echo(f"  🏢 Scoped to tenant '{tenant_obj.name}'")

                    except ImportError:
                        click.secho(
                            "  ❌ Error: Tenancy module is not available. "
                            "Remove --tenant or install tenancy support.",
                            fg="red", err=True,
                        )
                        return

                # ── User lookup ─────────────────────────────────────────
                # Build filter conditions based on provided identifiers
                conditions = []
                if email:
                    conditions.append(User.email == email)
                if username:
                    conditions.append(User.full_name == username)

                stmt = select(User).where(or_(*conditions))

                # Row-level tenancy: filter by tenant_id if tenant is
                # specified and the User model has a tenant_id column
                if tenant_obj and not tenant_obj.schema_name:
                    if hasattr(User, "tenant_id"):
                        stmt = stmt.where(User.tenant_id == tenant_obj.id)

                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    identifier = email or username
                    suffix = f" in tenant '{tenant}'" if tenant else ""
                    click.secho(
                        f"  ❌ Error: No user found matching '{identifier}'{suffix}.",
                        fg="red", err=True,
                    )
                    return

                # ── Authorization check ─────────────────────────────────
                if not (user.is_staff or user.is_superuser):
                    click.secho(
                        f"  ❌ Error: User '{user.email}' is not an admin or superuser. "
                        f"This command only changes passwords for privileged accounts.",
                        fg="red", err=True,
                    )
                    return

                # ── Password update ─────────────────────────────────────
                user.set_password(password)
                await session.flush()

                role = "superuser" if user.is_superuser else "admin"
                click.secho(
                    f"  ✅ Password changed successfully for {role}: {user.email}",
                    fg="green",
                )

            except Exception as e:
                click.secho(f"  ❌ Error changing password: {e}", fg="red", err=True)

            finally:
                # Always restore the search_path to prevent connection pool leaks
                if original_search_path is not None:
                    try:
                        await session.execute(
                            text(f"SET search_path TO {original_search_path}")
                        )
                    except Exception:
                        try:
                            await session.execute(text("SET search_path TO public"))
                        except Exception as e:
                            from eden.logging import get_logger
                            get_logger(__name__).error("Silent exception caught: %s", e, exc_info=True)

    asyncio.run(_change())
