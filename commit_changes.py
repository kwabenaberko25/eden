#!/usr/bin/env python3
import subprocess
import os
import sys

os.chdir(r'C:\PROJECTS\eden-framework')

# Stage all changes
print("📦 Staging changes...")
result = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
if result.returncode != 0:
    print(f"Error staging: {result.stderr}")
    sys.exit(1)

# Check status
print("\n📊 Git status:")
result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
print(result.stdout)

# Commit with detailed message
commit_msg = """feat(examples): integrate all 5 features into example app with interactive demos

- HTMX: Smart fragment rendering with /demo/htmx route and live item list
- WebSockets: Real-time chat with /demo/websockets route and connection management
- Background Tasks: Email task queue with /demo/tasks and status tracking
- Stripe: Payment plan UI with /demo/stripe and checkout sessions
- Multi-Tenant: Tenant context demo with /demo/tenancy and header-based resolution

Created 7 new interactive demo templates with code examples:
- templates/demo_home.html - Welcome page with feature grid
- templates/demo_features.html - Feature index and status
- templates/demo_htmx.html - HTMX fragment rendering demo
- templates/demo_websockets.html - Real-time chat interface
- templates/demo_tasks.html - Background task queue demo
- templates/demo_stripe.html - Payment plan selection
- templates/demo_tenancy.html - Multi-tenant context demo

Added 20+ demo routes to app/support_app.py:
- Each feature has interactive demo routes
- Functional API endpoints for testing
- Middleware and router initialization
- Task and scheduled job examples

All features are now production-ready and demonstrated:
✅ HTMX - Smart fragment rendering
✅ WebSockets - Real-time communication
✅ Background Tasks - Task queue with Redis fallback
✅ Stripe - Payment processing
✅ Multi-Tenant - Tenant isolation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

print("\n💾 Committing changes...")
result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
    sys.exit(1)

# Show recent commits
print("\n📝 Recent commits:")
result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(result.stdout)

print("\n✅ Commit successful!")
