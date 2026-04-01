"""
Eden CLI — Command-line interface for the Eden framework.

Available commands:
  eden run       - Start the development server
  eden new       - Scaffold a new project (minimal/standard/production)
  eden db        - Database migration management (init, migrate, upgrade, downgrade)
  eden auth      - Authentication management (createsuperuser, changepassword)
  eden generate  - Code generation (model, route)
  eden tasks     - Task queue management (worker, scheduler)
  eden version   - Print Eden version
"""

from eden.cli.main import cli

__all__ = ["cli"]
