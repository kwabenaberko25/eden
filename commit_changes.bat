@echo off
cd /d C:\PROJECTS\eden-framework

echo.
echo ===================================================
echo EDEN FRAMEWORK - COMMITTING FEATURE INTEGRATION
echo ===================================================
echo.

echo [1/3] Staging all changes...
git add -A
if errorlevel 1 (
    echo Error staging changes
    exit /b 1
)

echo [2/3] Creating commit...
git commit -m "feat(examples): integrate all 5 features into example app with interactive demos" -m "- HTMX: Smart fragment rendering with /demo/htmx route and live item list
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

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

if errorlevel 1 (
    echo Error creating commit
    exit /b 1
)

echo.
echo [3/3] Showing recent commits...
echo.
git log --oneline -5

echo.
echo ===================================================
echo ✅ COMMIT SUCCESSFUL!
echo ===================================================
echo.
echo Committed to: master
echo Feature: All 5 Eden Framework features integrated into example app
echo Templates: 7 new interactive demo templates created
echo Routes: 20+ new demo routes added
echo.
