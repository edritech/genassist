"""
Configuration settings for WebSocket microservice
"""

from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseSettings):
    """Redis connection configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    url: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL",
        description="Redis connection URL",
    )

    max_connections: int = Field(
        default=10,
        env="REDIS_MAX_CONNECTIONS",
        description="Maximum number of Redis connections in pool",
    )

    socket_timeout: int = Field(
        default=5,
        env="REDIS_SOCKET_TIMEOUT",
        description="Redis socket timeout in seconds",
    )

    health_check_interval: int = Field(
        default=30,
        env="REDIS_HEALTH_CHECK_INTERVAL",
        description="Redis health check interval in seconds",
    )


class JWTConfig(BaseSettings):
    """JWT authentication configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    secret_key: str = Field(
        default="your-jwt-secret-key-change-in-production",
        env="JWT_SECRET_KEY",
        description="JWT secret key (must match main API)",
    )

    algorithm: str = Field(
        default="HS256", env="JWT_ALGORITHM", description="JWT algorithm"
    )

    access_token_expire_minutes: int = Field(
        default=30,
        env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        description="JWT access token expiration time in minutes",
    )


class MultiTenantConfig(BaseSettings):
    """Multi-tenant configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    enabled: bool = Field(
        default=True, env="MULTI_TENANT_ENABLED", description="Enable multi-tenant mode"
    )

    default_tenant_id: Optional[str] = Field(
        default=None,
        env="DEFAULT_TENANT_ID",
        description="Default tenant ID for tenant-agnostic operations",
    )

    tenant_header_name: str = Field(
        default="X-Tenant-ID",
        env="TENANT_HEADER_NAME",
        description="HTTP header name for tenant ID",
    )

    tenant_query_param: str = Field(
        default="tenant_id",
        env="TENANT_QUERY_PARAM",
        description="Query parameter name for tenant ID",
    )

    tenant_id_pattern: str = Field(
        default=r"^[a-zA-Z0-9_-]+$",
        env="TENANT_ID_PATTERN",
        description="Regex pattern for valid tenant ID format",
    )

    max_tenant_id_length: int = Field(
        default=100,
        env="MAX_TENANT_ID_LENGTH",
        description="Maximum length for tenant ID",
    )


class ServiceURLsConfig(BaseSettings):
    """Service URLs configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    metrics_path: str = Field(
        default="/metrics", env="METRICS_PATH", description="Metrics endpoint path"
    )

    health_check_path: str = Field(
        default="/health",
        env="HEALTH_CHECK_PATH",
        description="Health check endpoint path",
    )


class WebSocketConfig(BaseSettings):
    """WebSocket specific configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    heartbeat_interval: int = Field(
        default=30,
        env="WEBSOCKET_HEARTBEAT_INTERVAL",
        description="WebSocket heartbeat interval in seconds",
    )

    max_connections_per_user: int = Field(
        default=10,
        env="MAX_CONNECTIONS_PER_USER",
        description="Maximum WebSocket connections per user",
    )

    connection_timeout: int = Field(
        default=300,
        env="WEBSOCKET_CONNECTION_TIMEOUT",
        description="WebSocket connection timeout in seconds",
    )

    message_size_limit: int = Field(
        default=1024 * 1024,  # 1MB
        env="WEBSOCKET_MESSAGE_SIZE_LIMIT",
        description="Maximum WebSocket message size in bytes",
    )

    enable_compression: bool = Field(
        default=True,
        env="WEBSOCKET_ENABLE_COMPRESSION",
        description="Enable WebSocket compression",
    )


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT",
        description="Log message format",
    )

    enable_json_logs: bool = Field(
        default=False,
        env="ENABLE_JSON_LOGS",
        description="Enable JSON structured logging",
    )


class CoreServiceConfig(BaseSettings):
    """Core service configuration for service-to-service communication"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    base_url: str = Field(
        default="http://localhost:8000",
        env="CORE_SERVICE_BASE_URL",
        description="Base URL of the core service (use Docker service name in containers)",
    )

    internal_api_key: Optional[str] = Field(
        default=None,
        env="INTERNAL_API_KEY",
        description="API key for internal service-to-service authentication",
    )

    timeout: float = Field(
        default=5.0,
        env="CORE_SERVICE_TIMEOUT",
        description="Timeout for core service requests in seconds",
    )


class Settings(BaseSettings):
    """Main settings class that combines all configuration sections"""

    SERVICE_NAME: str = "genassist-websocket"
    SERVICE_VERSION: str = "1.0.0"

    # # Service information
    # SERVICE_NAME: str = Field(
    #     default="GenAssist WebSocket Service",
    #     env="SERVICE_NAME",
    #     description="Name of this service",
    # )

    # SERVICE_VERSION: str = Field(
    #     default="1.0.0",
    #     env="SERVICE_VERSION",
    #     description="Version of this service",
    # )

    ENV: str = Field(
        default="development",
        env="ENV",
        description="Environment (development, test, production)",
    )

    host: str = Field(default="0.0.0.0", env="HOST", description="Service host address")
    port: int = Field(default=8002, env="PORT", description="Service port")
    debug: bool = Field(default=False, env="DEBUG", description="Enable debug mode")

    # Configuration sections
    redis: RedisConfig = Field(default_factory=RedisConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    multi_tenant: MultiTenantConfig = Field(default_factory=MultiTenantConfig)
    service_urls: ServiceURLsConfig = Field(default_factory=ServiceURLsConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    core_service: CoreServiceConfig = Field(default_factory=CoreServiceConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENV.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENV.lower() == "development"


# Global settings instance
settings: Settings = Settings()


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings: Global settings object
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    Returns:
        Settings: New settings instance
    """
    global settings
    settings = Settings()
    return settings


# Configuration validation functions
def validate_settings() -> List[str]:
    """
    Validate critical settings and return list of issues.

    Returns:
        List[str]: List of validation issues (empty if all valid)
    """
    issues = []

    # Validate JWT secret
    if settings.jwt.secret_key == "your-jwt-secret-key-change-in-production":
        if settings.is_production():
            issues.append("JWT secret key must be changed in production")

    # Validate Redis URL
    if not settings.redis.url:
        issues.append("Redis URL is required")

    # Validate multi-tenant settings
    if settings.multi_tenant.enabled and settings.multi_tenant.max_tenant_id_length < 1:
        issues.append("Max tenant ID length must be at least 1")

    # Validate WebSocket settings
    if settings.websocket.max_connections_per_user < 1:
        issues.append("Max connections per user must be at least 1")

    if settings.websocket.message_size_limit < 1024:
        issues.append("Message size limit must be at least 1024 bytes")

    return issues


def get_redis_connection_string() -> str:
    """
    Get Redis connection string with parameters.

    Returns:
        str: Redis connection string
    """
    return settings.redis.url


def get_jwt_secret_key() -> str:
    """
    Get JWT secret key.

    Returns:
        str: JWT secret key
    """
    return settings.jwt.secret_key


def is_multi_tenant_enabled() -> bool:
    """
    Check if multi-tenant mode is enabled.

    Returns:
        bool: True if multi-tenant is enabled
    """
    return settings.multi_tenant.enabled
