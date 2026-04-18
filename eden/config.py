from __future__ import annotations
"""
Eden — Configuration Management

Centralized configuration system with schema validation, environment support,
and secrets management. Supports dev/prod configs, environment variables,
and .env file loading.

**Features:**
- Pydantic-based schema validation
- Environment-specific configs (dev, test, prod)
- .env file support (python-dotenv)
- Secrets management with safe defaults
- Config inheritance and overrides

**Usage:**

    from eden.config import get_config, Config
    
    # Get active config (auto-detected from EDEN_ENV)
    config = get_config()
    
    # Create custom config
    custom_config = Config(
        debug=True,
        database_url="sqlite+aiosqlite:///dev.db",
        secret_key="dev-secret-key"
    )
    
    # Access settings
    print(config.database_url)
    print(config.debug)

**Environment Variables:**
    - EDEN_ENV: dev|test|prod (default: dev)
    - EDEN_DEBUG: true|false (overrides config)
    - DATABASE_URL: Database connection string
    - SECRET_KEY: Application secret (required in prod)
    - STRIPE_API_KEY: Stripe API key
    - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY: AWS credentials
    - REDIS_URL: Redis connection string
    
**Environment Files:**
    Create a .env file in the project root:
    
    EDEN_ENV=dev
    DEBUG=true
    DATABASE_URL=sqlite+aiosqlite:///dev.db
    SECRET_KEY=local-dev-secret
    STRIPE_API_KEY=sk_test_...

**Config Modes:**
    - dev: Debug enabled, permissive validation, local DB
    - test: Isolation, in-memory DB, mocked external services
    - prod: Strict validation, all secrets required, optimized defaults
"""


import os
from enum import Enum
from typing import Optional, Any, Dict
from pathlib import Path
from functools import cached_property

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
except ImportError:
    raise ImportError(
        "pydantic is required for configuration. "
        "Install with: pip install pydantic"
    )


class Environment(str, Enum):
    """Supported environment modes."""
    DEV = "dev"
    TEST = "test"
    TESTING = "testing"
    PROD = "prod"


class Config(BaseModel):
    """
    Configuration schema for Eden applications.
    
    All configuration is validated at instantiation. Environment-specific
    defaults are applied based on EDEN_ENV.
    
    Attributes:
        env: Environment mode (dev|test|prod)
        debug: Enable debug mode and detailed error messages
        secret_key: Secret key for signing (required in prod)
        database_url: Database connection string
        
        # Auth & Secrets
        jwt_secret: Secret for JWT token signing
        oauth_providers: Dict of OAuth provider configs
        
        # External Services
        stripe_api_key: Stripe API key (optional)
        stripe_webhook_secret: Stripe webhook secret (optional)
        aws_access_key_id: AWS credentials for S3 (optional)
        aws_secret_access_key: AWS credentials for S3 (optional)
        aws_s3_bucket: AWS S3 bucket name (optional)
        aws_s3_region: AWS S3 region (default: us-east-1)
        
        # Caching & Real-time
        redis_url: Redis connection string (optional)
        cache_ttl: Default cache TTL in seconds (default: 3600)
        
        # App Settings
        title: Application title (default: Eden)
        version: Application version (default: 0.1.0)
        log_level: Logging level (default: INFO)
        
        # Security
        allowed_hosts: List of allowed hostnames
        cors_origins: List of CORS allowed origins
        csrf_cookie_secure: CSRF cookie secure flag (default: True in prod)
        csrf_cookie_httponly: CSRF cookie httponly flag (default: True)
        
        # Pagination
        page_size: Default pagination size (default: 20)
        
        # Messaging
        messages_session_key: Session key for flash messages (default: _eden_messages)
        
        # Observability
        metrics_enabled: Enable Prometheus metrics endpoint (/metrics)
        metrics_url: URL path for metrics exposition
    """
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        arbitrary_types_allowed=True,
    )
    
    # Environment
    env: Environment = Field(default=Environment.DEV, description="Environment mode")
    debug: Optional[bool] = Field(default=None, description="Enable debug mode")
    
    # Core secrets
    secret_key: str = Field(
        default="",
        description="Secret key for signing (required in prod)"
    )
    
    # Database
    database_url: str = Field(
        default="",
        description="Database connection string"
    )
    db_strict_session_mode: bool = Field(
        default=False,
        description="If True, prevents silent DB session auto-instantiation in background contexts."
    )
    
    # Database Connection Pool
    db_pool_size: int = Field(
        default=10,
        description="Number of persistent connections in the pool",
        ge=1
    )
    db_max_overflow: int = Field(
        default=20,
        description="Max additional connections beyond pool_size under load",
        ge=0
    )
    db_pool_recycle: int = Field(
        default=3600,
        description="Recycle connections after this many seconds (prevents stale connections)"
    )
    db_pool_timeout: int = Field(
        default=30,
        description="Seconds to wait for a connection before timing out",
        ge=1
    )
    db_pool_pre_ping: bool = Field(
        default=True,
        description="Test connections for liveness before checking out from the pool"
    )
    db_echo: bool = Field(
        default=False,
        description="Echo SQL statements to log (useful for debugging)"
    )
    
    # Auth & Tokens
    jwt_secret: str = Field(
        default="",
        description="Secret for JWT token signing"
    )
    oauth_providers: Dict[str, Any] = Field(
        default_factory=dict,
        description="OAuth provider configurations"
    )
    
    # External Services (Secrets)
    stripe_api_key: str = Field(
        default="",
        description="Stripe API key"
    )
    stripe_webhook_secret: str = Field(
        default="",
        description="Stripe webhook secret"
    )
    
    # AWS / Storage
    aws_access_key_id: str = Field(
        default="",
        description="AWS access key"
    )
    aws_secret_access_key: str = Field(
        default="",
        description="AWS secret key"
    )
    aws_s3_bucket: str = Field(
        default="",
        description="AWS S3 bucket name"
    )
    aws_s3_region: str = Field(
        default="us-east-1",
        description="AWS S3 region"
    )
    
    # Cache & Real-time
    redis_url: str = Field(
        default="",
        description="Redis connection string (e.g., redis://localhost:6379). "
                    "Leave empty for in-memory fallback (tasks, caching, pub/sub will be local-only)."
    )
    cache_ttl: int = Field(
        default=3600,
        description="Default cache TTL in seconds"
    )
    
    # App Information
    title: str = Field(
        default="Eden",
        description="Application title"
    )
    version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Security
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "*"],
        description="Allowed hostnames"
    )
    cors_origins: list[str] = Field(
        default_factory=list,
        description="CORS allowed origins"
    )
    csrf_cookie_secure: bool = Field(
        default=True,
        description="CSRF cookie secure flag"
    )
    csrf_cookie_httponly: bool = Field(
        default=True,
        description="CSRF cookie httponly flag"
    )
    
    # Pagination
    page_size: int = Field(
        default=20,
        description="Default pagination size"
    )
    
    # Messaging
    messages_session_key: str = Field(
        default="_eden_messages",
        description="Session key for flash messages"
    )
    
    # Observability
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint (/metrics)"
    )
    metrics_url: str = Field(
        default="/metrics",
        description="URL path for metrics exposition"
    )
    
    # Development
    browser_reload: bool = Field(
        default=True,
        description="Enable browser auto-reload on code changes"
    )
    
    @field_validator("env", mode="before")
    @classmethod
    def validate_env(cls, v: Any) -> Environment:
        """Convert string to Environment enum."""
        if isinstance(v, Environment):
            return v
        if isinstance(v, str):
            v = v.lower()
            return Environment(v)
        raise ValueError(f"Invalid environment: {v}")
    
    @field_validator("debug", mode="before")
    @classmethod
    def validate_debug_before(cls, v: Any) -> Any:
        """Coerce strings to boolean before validation."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return v
    
    @model_validator(mode="after")
    def validate_after_init(self) -> Config:
        """Validate configuration after all fields are initialized."""
        # Set debug default if not explicitly set
        if self.debug is None:
            self.debug = self.env in (Environment.DEV, Environment.TEST)
        
        # Auto-generate secret_key in dev and test modes
        if not self.secret_key and self.env in (Environment.DEV, Environment.TEST):
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
        
        # Set redis_url default in dev mode
        if not self.redis_url and self.env == Environment.DEV:
            self.redis_url = "redis://localhost:6379"
        
        # Validate secret_key in production
        if self.env == Environment.PROD and not self.secret_key:
            raise ValueError(
                "secret_key is required in production. "
                "Set SECRET_KEY environment variable."
            )
        
        # JWT secret defaults to secret_key
        if not self.jwt_secret:
            if self.secret_key:
                self.jwt_secret = self.secret_key
            elif self.env == Environment.TEST:
                import secrets
                self.jwt_secret = secrets.token_urlsafe(32)
        
        return self
    
    @cached_property
    def expensive_setting_example(self) -> Any:
        """
        Example of a lazy-loaded setting.
        Use cached_property for settings that are expensive to compute 
        (e.g., loading an SSL certificate) to improve performance on subsequent accesses.
        """
        return None
        
    def get_database_url(self) -> str:
        """
        Get database URL with environment-specific defaults.
        
        Returns:
            Database connection string
        """
        if self.database_url:
            return self.database_url
        
        # Defaults by environment
        if self.env == Environment.TEST:
            return "sqlite+aiosqlite:///:memory:"
        elif self.env == Environment.PROD:
            raise ValueError(
                "database_url is required in production. "
                "Set DATABASE_URL environment variable."
            )
        else:  # dev
            return "sqlite+aiosqlite:///eden.db"
    
    def get_database_engine_kwargs(self) -> Dict[str, Any]:
        """
        Build SQLAlchemy engine keyword arguments from config pool settings.
        
        Returns a dict suitable for passing directly to ``Database(url, **kwargs)``
        or ``create_async_engine(url, **kwargs)``.
        
        Connection pool settings are only applied for non-SQLite databases,
        since SQLite uses different pooling behavior.
        
        Returns:
            Dict of engine keyword arguments.
        
        Example:
            config = get_config()
            db = Database(config.get_database_url(), **config.get_database_engine_kwargs())
        """
        kwargs: Dict[str, Any] = {
            "pool_pre_ping": self.db_pool_pre_ping,
            "echo": self.db_echo,
        }
        
        url = self.get_database_url()
        # Set safe defaults for connection pooling when not explicitly provided.
        # This helps prevent resource exhaustion in production.
        # SQLite dialects do not support these parameters.
        if not url.startswith("sqlite"):
            poolclass = kwargs.get("poolclass")
            if poolclass not in (StaticPool, NullPool):
                kwargs.setdefault("pool_size", 10)
                kwargs.setdefault("max_overflow", 20)
                kwargs.setdefault("pool_recycle", 3600)
            
            kwargs.setdefault("pool_timeout", 30)

        kwargs.setdefault("pool_pre_ping", True)
        kwargs.setdefault("echo", False)
        
        return kwargs
    
    def is_prod(self) -> bool:
        """Check if running in production."""
        return self.env == Environment.PROD
    
    def is_dev(self) -> bool:
        """Check if running in development."""
        return self.env == Environment.DEV
    
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.env == Environment.TEST


class ConfigManager:
    """
    Global configuration manager singleton.
    
    Loads configuration from environment variables and .env file,
    with environment-specific defaults.
    
    **Usage:**
    
        config = ConfigManager.instance()
        print(config.get().database_url)
    """
    
    _instance: Optional[ConfigManager] = None
    _config: Optional[Config] = None
    
    def __new__(cls) -> ConfigManager:
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def instance(cls) -> ConfigManager:
        """Get singleton instance."""
        return cls()
    
    def load(self, env_file: Optional[Path | str] = None) -> Config:
        """
        Load configuration from environment.
        
        Environment detection order:
        1. EDEN_ENV environment variable
        2. Environment-specific .env.{env} file
        3. Default .env file
        4. Built-in defaults
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        
        Returns:
            Loaded Config instance
        """
        # Detect environment first to load correct .env file
        current_env = os.getenv("EDEN_ENV", "dev").lower()
        
        # Determine files to load
        if not env_file:
            # Use the project root directory, not just the working directory. 
            # This prevents issues when running from different locations.
            project_root = Path(__file__).resolve().parent.parent
            env_file = project_root / ".env"
            
        if isinstance(env_file, str):
            env_file = Path(env_file)
            
        env_specific_file = env_file.parent / f".env.{current_env}"
        
        # Load order (precedence from high to low):
        # 1. os.environ (always honored by load_dotenv(override=False))
        # 2. .env.{env}
        # 3. .env
        
        try:
            from dotenv import load_dotenv
            
            # Load env-specific first, then generic
            if env_specific_file.exists():
                load_dotenv(env_specific_file, override=False)
                
            if env_file.exists():
                load_dotenv(env_file, override=False)
        except ImportError:
            pass
        
        # Create config from environment variables
        # We allow Pydantic to handle more complex types downstream if needed
        self._config = Config(
            env=os.getenv("EDEN_ENV", "dev"),
            debug=os.getenv("EDEN_DEBUG", os.getenv("DEBUG")) or None,
            secret_key=os.getenv("SECRET_KEY", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            stripe_api_key=os.getenv("STRIPE_API_KEY", ""),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_s3_bucket=os.getenv("AWS_S3_BUCKET", ""),
            aws_s3_region=os.getenv("AWS_S3_REGION", "us-east-1"),
            redis_url=os.getenv("REDIS_URL", ""),
            cache_ttl=int(os.getenv("CACHE_TTL", "3600")),
            title=os.getenv("EDEN_TITLE", os.getenv("TITLE", "Eden")),
            version=os.getenv("EDEN_VERSION", os.getenv("VERSION", "1.0.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            allowed_hosts=os.getenv("ALLOWED_HOSTS", "*").split(","),
            cors_origins=os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [],
            messages_session_key=os.getenv("EDEN_MESSAGES_SESSION_KEY", "_eden_messages"),
            metrics_enabled=os.getenv("EDEN_METRICS_ENABLED", "true").lower() in ("true", "1", "yes"),
            metrics_url=os.getenv("EDEN_METRICS_URL", "/metrics"),
            browser_reload=os.getenv("EDEN_BROWSER_RELOAD", "true").lower() in ("true", "1", "yes"),
        )
        
        return self._config
    
    def get(self) -> Config:
        """
        Get current configuration.
        
        Loads configuration on first call if not already loaded.
        
        Returns:
            Config instance
        """
        if self._config is None:
            self.load()
        return self._config
    
    def reset(self) -> None:
        """
        Reset configuration state. 
        
        After reset(), the next call to get() will re-load from environment.
        This is REQUIRED in test fixtures to prevent state leakage between tests.
        
        Usage (pytest fixture):
            @pytest.fixture(autouse=True)
            def reset_config():
                yield
                ConfigManager.instance().reset()
        """
        self._config = None
    
    def set(self, config: Config) -> None:
        """Set configuration directly (useful for testing)."""
        self._config = config


def get_config() -> Config:
    """
    Get active configuration.
    
    Convenience function for accessing the global config.
    
    Returns:
        Config instance
    
    **Example:**
    
        from eden.config import get_config
        config = get_config()
        db = Database(config.get_database_url())
        await db.connect()
    """
    return ConfigManager.instance().get()


def set_config(config: Config) -> None:
    """
    Set active configuration.
    
    Useful for testing or dynamic configuration updates.
    
    Args:
        config: Config instance to set
    
    **Example:**
    
        from eden.config import set_config, Config
        config = Config(debug=True)
        set_config(config)
    """
    ConfigManager.instance().set(config)


def create_config(env: str = "dev", **kwargs) -> Config:
    """
    Create a configuration instance.
    
    Useful for testing or custom configurations.
    
    Args:
        env: Environment mode (dev|test|prod)
        **kwargs: Additional configuration options
    
    Returns:
        Config instance
    
    **Example:**
    
        test_config = create_config(
            env="test",
            database_url="sqlite+aiosqlite:///:memory:",
            debug=True
        )
    """
    if isinstance(env, str):
        env_name = env.lower()
    else:
        env_name = env.value if hasattr(env, "value") else str(env).lower()

    # Auto-generate secret_key for dev/test if not provided
    if "secret_key" not in kwargs and env_name in ("dev", "test"):
        import secrets
        kwargs["secret_key"] = secrets.token_urlsafe(32)

    # Auto-generate redis_url for dev if not provided
    if "redis_url" not in kwargs and env_name == "dev":
        kwargs["redis_url"] = "redis://localhost:6379"

    return Config(env=env, **kwargs)
