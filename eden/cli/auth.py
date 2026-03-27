"""
Eden — Authentication CLI Commands
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
