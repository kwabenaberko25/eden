from eden import Eden, setup_logging
from .settings import DEBUG, SECRET_KEY, DATABASE_URL, LOG_LEVEL, LOG_FORMAT
from .routes import main_router

def create_app() -> Eden:
    # Configure logging
    setup_logging(level=LOG_LEVEL, json_format=(LOG_FORMAT == "json"))

    app = Eden(
        title="my_test_project",
        debug=DEBUG
    )

    # Routes
    app.include_router(main_router)

    # Security middleware (production defaults)
    app.add_middleware("security")
    app.add_middleware("ratelimit", max_requests=200, window_seconds=60)
    app.add_middleware("logging")

    # Health checks
    app.enable_health_checks()

    return app

app = create_app()
