"""
Eden — Authentication CLI Commands
"""

import asyncio

import click

from eden.auth.models import User
from eden.orm import Database


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
        # Setup DB (assuming sqlite for now, but should use config)
        # Real implementation would load from eden.conf or similar
        db = Database("sqlite+aiosqlite:///db.sqlite3")

        async with db.get_session() as session:
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
                    roles=["admin"],
                    permissions=["*"]
                )
                user.set_password(password)

                session.add(user)
                await session.commit()
                click.echo(f"Successfully created superuser: {email}")

            except Exception as e:
                click.echo(f"Error creating superuser: {e}")

    asyncio.run(_create())
