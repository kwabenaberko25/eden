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

from __future__ import annotations

import os
from enum import Enum
from typing import Optional, Any, Dict
from pathlib import Path

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
except ImportError:
    raise ImportError(
        "pydantic is required for configuration. "
        "Install with: pip install pydantic"
    )


class Environment(str, Enum):
    """Supported environment modes."""
    DEV = "dev"
    TEST = "test"
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
    """
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields for custom config
    
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
        default="redis://localhost:6379",
        description="Redis connection string"
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
        default="0.1.0",
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
        
        # Validate secret_key in production
        if self.env == Environment.PROD and not self.secret_key:
            raise ValueError(
                "secret_key is required in production. "
                "Set SECRET_KEY environment variable."
            )
        
        # Auto-generate secrets in dev/test
        if not self.secret_key and self.env in (Environment.DEV, Environment.TEST):
            import secrets
            self.secret_key = secrets.token_urlsafe(32)
        
        # JWT secret defaults to secret_key
        if not self.jwt_secret:
            if self.secret_key:
                self.jwt_secret = self.secret_key
            elif self.env in (Environment.DEV, Environment.TEST):
                import secrets
                self.jwt_secret = secrets.token_urlsafe(32)
        
        return self
    
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
        
        Raises:
            ValueError: If required secrets are missing
        """
        # Load .env file if exists
        env_file = env_file or Path.cwd() / ".env"
        if isinstance(env_file, str):
            env_file = Path(env_file)
        
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                # Silently skip if python-dotenv not installed
                # (Configuration can still use env vars)
                pass
        
        # Load environment-specific .env file
        current_env = os.getenv("EDEN_ENV", "dev").lower()
        env_specific_file = env_file.parent / f".env.{current_env}"
        if env_specific_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_specific_file, override=True)
            except ImportError:
                pass
        
        # Create config from environment variables
        self._config = Config(
            env=os.getenv("EDEN_ENV", "dev"),
            debug=os.getenv("EDEN_DEBUG", os.getenv("DEBUG", "")).lower() in ("true", "1"),
            secret_key=os.getenv("SECRET_KEY", ""),
            database_url=os.getenv("DATABASE_URL", ""),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            stripe_api_key=os.getenv("STRIPE_API_KEY", ""),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_s3_bucket=os.getenv("AWS_S3_BUCKET", ""),
            aws_s3_region=os.getenv("AWS_S3_REGION", "us-east-1"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            cache_ttl=int(os.getenv("CACHE_TTL", "3600")),
            title=os.getenv("EDEN_TITLE", "Eden"),
            version=os.getenv("EDEN_VERSION", "0.1.0"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            messages_session_key=os.getenv("EDEN_MESSAGES_SESSION_KEY", "_eden_messages"),
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
        """Reset configuration (useful for testing)."""
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
    return Config(env=env, **kwargs)
