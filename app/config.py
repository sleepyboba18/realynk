import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required application configuration is invalid."""


_DEFAULT_DATABASE_URL = "postgresql+psycopg://user:pass@localhost:5432/realynk_test"
_ALLOWED_ENVIRONMENTS = {"development", "testing", "production"}
_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _coalesce_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    if value.lower() in {"change-me", "change-me-too"}:
        return default
    return value



def _as_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ConfigurationError(f"{name}: expected true/false, 1/0, or yes/no")



def _as_int(value: str, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name}: expected an integer") from exc


def _positive(value: int, name: str, maximum: int | None = None) -> int:
    if value <= 0 or (maximum is not None and value > maximum):
        suffix = f" and at most {maximum}" if maximum is not None else ""
        raise ConfigurationError(f"{name}: expected a positive integer{suffix}")
    return value


def _database_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgresql+psycopg"} or not parsed.hostname or not parsed.path.strip("/"):
        raise ConfigurationError("DATABASE_URL: expected a PostgreSQL SQLAlchemy URL")
    return value


@dataclass(frozen=True)
class Config:
    app_name: str
    app_env: str
    debug: bool
    host: str
    port: int
    database_url: str
    secret_key: str
    jwt_secret_key: str
    jwt_access_token_expires_minutes: int
    cors_origins: str | list[str]
    database_pool_recycle: int
    database_pool_size: int
    database_max_overflow: int
    typing_timeout_seconds: int
    notification_retention_days: int
    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket: str
    max_attachment_size_mb: int
    max_total_attachment_size_mb: int
    max_attachments_per_message: int
    attachment_signed_url_expires_seconds: int
    rate_limit_enabled: bool
    rate_limit_default_requests: int
    rate_limit_default_window_seconds: int
    auth_rate_limit_requests: int
    auth_rate_limit_window_seconds: int
    socket_rate_limit_events: int
    socket_rate_limit_window_seconds: int
    max_request_body_size_bytes: int
    max_query_params: int
    max_header_size: int
    trust_proxy: bool
    cors_allow_credentials: bool
    cors_allowed_methods: list[str]
    cors_allowed_headers: list[str]
    socketio_max_http_buffer_size: int
    hsts_enabled: bool
    log_level: str
    log_format: str
    metrics_enabled: bool
    metrics_endpoint_enabled: bool
    slow_request_threshold_ms: int
    database_pool_timeout: int
    jwt_algorithm: str

    @classmethod
    def from_environment(cls) -> "Config":
        load_dotenv()

        app_env = os.getenv("APP_ENV", "development").strip().lower() or "development"
        if app_env not in _ALLOWED_ENVIRONMENTS:
            raise ConfigurationError("APP_ENV: expected development, testing, or production")
        raw_database_url = os.getenv("DATABASE_URL", "").strip()
        if app_env == "production" and not raw_database_url:
            raise ConfigurationError("DATABASE_URL: required in production")
        placeholder_database_url = "postgresql+psycopg://USERNAME:PASSWORD@HOST:PORT/DATABASE"
        if raw_database_url == placeholder_database_url:
            if app_env == "production":
                raise ConfigurationError("DATABASE_URL: replace the documented placeholder with a PostgreSQL URL")
            raw_database_url = ""
        database_url = _database_url(raw_database_url or _DEFAULT_DATABASE_URL)

        raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "*")).strip() or "*"
        cors_origins: str | list[str] = (
            "*"
            if raw_origins == "*"
            else [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        )
        if not cors_origins:
            raise ConfigurationError("CORS_ORIGINS must contain '*' or at least one origin")

        secret_key = os.getenv("SECRET_KEY", "").strip() or "development-secret-key-please-change"
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", os.getenv("JWT_SECRET", "")).strip() or "development-jwt-secret-key-please-change"
        if app_env == "production" and not os.getenv("SECRET_KEY", "").strip():
            raise ConfigurationError("SECRET_KEY: required in production")
        if app_env == "production" and not os.getenv("JWT_SECRET_KEY", os.getenv("JWT_SECRET", "")).strip():
            raise ConfigurationError("JWT_SECRET_KEY: required in production")
        if app_env == "production" and secret_key.lower() in {"secret", "changeme", "change-me", "password", "test"}:
            raise ConfigurationError("SECRET_KEY: insecure production secret")
        if app_env == "production" and jwt_secret_key.lower() in {"secret", "changeme", "change-me", "password", "test"}:
            raise ConfigurationError("JWT_SECRET_KEY: insecure production secret")
        if jwt_secret_key == secret_key:
            raise ConfigurationError("JWT_SECRET_KEY must differ from SECRET_KEY")
        debug = _as_bool(os.getenv("DEBUG", "true" if app_env == "development" else "false"), "DEBUG")
        if app_env == "production" and debug:
            raise ConfigurationError("DEBUG: must be false in production")
        cors_allow_credentials = _as_bool(os.getenv("CORS_ALLOW_CREDENTIALS", "false"), "CORS_ALLOW_CREDENTIALS")
        if app_env == "production" and cors_allow_credentials and cors_origins == "*":
            raise ConfigurationError("CORS_ALLOWED_ORIGINS: wildcard is invalid with credentials")
        jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()
        if jwt_algorithm != "HS256":
            raise ConfigurationError("JWT_ALGORITHM: only HS256 is supported")
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in _ALLOWED_LOG_LEVELS:
            raise ConfigurationError("LOG_LEVEL: expected DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        log_format = os.getenv("LOG_FORMAT", "json" if app_env == "production" else "text").strip().lower()
        if log_format not in {"json", "text"}:
            raise ConfigurationError("LOG_FORMAT: expected json or text")
        port = _as_int(os.getenv("PORT", "5000"), "PORT")
        if not 1 <= port <= 65535:
            raise ConfigurationError("PORT: expected an integer from 1 to 65535")
        pool_size = _positive(_as_int(os.getenv("DATABASE_POOL_SIZE", "5"), "DATABASE_POOL_SIZE"), "DATABASE_POOL_SIZE", 100)
        max_overflow = _as_int(os.getenv("DATABASE_MAX_OVERFLOW", "2"), "DATABASE_MAX_OVERFLOW")
        if max_overflow < 0 or max_overflow > 100:
            raise ConfigurationError("DATABASE_MAX_OVERFLOW: expected an integer from 0 to 100")
        rate_values = (
            ("RATE_LIMIT_DEFAULT_REQUESTS", "120"),
            ("RATE_LIMIT_DEFAULT_WINDOW_SECONDS", "60"),
            ("AUTH_RATE_LIMIT_REQUESTS", "10"),
            ("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"),
            ("SOCKET_RATE_LIMIT_EVENTS", "60"),
            ("SOCKET_RATE_LIMIT_WINDOW_SECONDS", "60"),
        )
        parsed_rates = {name: _positive(_as_int(os.getenv(name, default), name), name, 1_000_000) for name, default in rate_values}
        max_attachment_size_mb = _positive(_as_int(os.getenv("MAX_ATTACHMENT_SIZE_MB", "25"), "MAX_ATTACHMENT_SIZE_MB"), "MAX_ATTACHMENT_SIZE_MB")
        max_total_attachment_size_mb = _positive(_as_int(os.getenv("MAX_TOTAL_ATTACHMENT_SIZE_MB", "50"), "MAX_TOTAL_ATTACHMENT_SIZE_MB"), "MAX_TOTAL_ATTACHMENT_SIZE_MB")
        if max_total_attachment_size_mb < max_attachment_size_mb:
            raise ConfigurationError("MAX_TOTAL_ATTACHMENT_SIZE_MB: must be at least MAX_ATTACHMENT_SIZE_MB")

        return cls(
            app_name=os.getenv("APP_NAME", "Realynk").strip() or "Realynk",
            app_env=app_env,
            debug=debug,
            host=os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=port,
            database_url=database_url,
            secret_key=secret_key,
            jwt_secret_key=jwt_secret_key,
            jwt_access_token_expires_minutes=_positive(_as_int(
                os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"),
                "JWT_ACCESS_TOKEN_EXPIRES_MINUTES",
            ), "JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 60 * 24 * 30),
            cors_origins=cors_origins,
            database_pool_recycle=_as_int(
                os.getenv("DATABASE_POOL_RECYCLE", "1800"),
                "DATABASE_POOL_RECYCLE",
            ),
            database_pool_size=_as_int(
                str(pool_size), "DATABASE_POOL_SIZE"
            ),
            database_max_overflow=_as_int(
                str(max_overflow), "DATABASE_MAX_OVERFLOW"
            ),
            database_pool_timeout=_positive(_as_int(os.getenv("DB_POOL_TIMEOUT", "30"), "DB_POOL_TIMEOUT"), "DB_POOL_TIMEOUT"),
            typing_timeout_seconds=_as_int(
                os.getenv("TYPING_TIMEOUT_SECONDS", "5"), "TYPING_TIMEOUT_SECONDS"
            ),
            notification_retention_days=_as_int(
                os.getenv("NOTIFICATION_RETENTION_DAYS", "90"),
                "NOTIFICATION_RETENTION_DAYS",
            ),
            supabase_url=os.getenv("SUPABASE_URL", "").strip(),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            supabase_storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "realynk-attachments").strip() or "realynk-attachments",
            max_attachment_size_mb=max_attachment_size_mb,
            max_total_attachment_size_mb=max_total_attachment_size_mb,
            max_attachments_per_message=_positive(_as_int(os.getenv("MAX_ATTACHMENTS_PER_MESSAGE", "10"), "MAX_ATTACHMENTS_PER_MESSAGE"), "MAX_ATTACHMENTS_PER_MESSAGE"),
            attachment_signed_url_expires_seconds=_positive(_as_int(os.getenv("ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS", "600"), "ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS"), "ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS"),
            rate_limit_enabled=_as_bool(os.getenv("RATE_LIMIT_ENABLED", "true"), "RATE_LIMIT_ENABLED"),
            rate_limit_default_requests=parsed_rates["RATE_LIMIT_DEFAULT_REQUESTS"],
            rate_limit_default_window_seconds=parsed_rates["RATE_LIMIT_DEFAULT_WINDOW_SECONDS"],
            auth_rate_limit_requests=parsed_rates["AUTH_RATE_LIMIT_REQUESTS"],
            auth_rate_limit_window_seconds=parsed_rates["AUTH_RATE_LIMIT_WINDOW_SECONDS"],
            socket_rate_limit_events=parsed_rates["SOCKET_RATE_LIMIT_EVENTS"],
            socket_rate_limit_window_seconds=parsed_rates["SOCKET_RATE_LIMIT_WINDOW_SECONDS"],
            max_request_body_size_bytes=_positive(_as_int(os.getenv("MAX_REQUEST_BODY_SIZE_BYTES", str(5 * 1024 * 1024)), "MAX_REQUEST_BODY_SIZE_BYTES"), "MAX_REQUEST_BODY_SIZE_BYTES"),
            max_query_params=_as_int(os.getenv("MAX_QUERY_PARAMS", "50"), "MAX_QUERY_PARAMS"),
            max_header_size=_as_int(os.getenv("MAX_HEADER_SIZE", "8192"), "MAX_HEADER_SIZE"),
            trust_proxy=_as_bool(os.getenv("TRUST_PROXY", "false"), "TRUST_PROXY"),
            cors_allow_credentials=cors_allow_credentials,
            cors_allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            cors_allowed_headers=["Content-Type", "Authorization", "X-Request-ID"],
            socketio_max_http_buffer_size=_positive(_as_int(os.getenv("SOCKETIO_MAX_HTTP_BUFFER_SIZE", str(5 * 1024 * 1024)), "SOCKETIO_MAX_HTTP_BUFFER_SIZE"), "SOCKETIO_MAX_HTTP_BUFFER_SIZE"),
            hsts_enabled=_as_bool(os.getenv("HSTS_ENABLED", "false"), "HSTS_ENABLED"),
            log_level=log_level,
            log_format=log_format,
            metrics_enabled=_as_bool(os.getenv("METRICS_ENABLED", "true"), "METRICS_ENABLED"),
            metrics_endpoint_enabled=_as_bool(os.getenv("METRICS_ENDPOINT_ENABLED", "true"), "METRICS_ENDPOINT_ENABLED"),
            slow_request_threshold_ms=_positive(_as_int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "1000"), "SLOW_REQUEST_THRESHOLD_MS"), "SLOW_REQUEST_THRESHOLD_MS"),
            jwt_algorithm=jwt_algorithm,
        )

    def flask_settings(self) -> dict[str, object]:
        return {
            "APP_NAME": self.app_name,
            "APP_ENV": self.app_env,
            "DEBUG": self.debug,
            "TESTING": self.app_env == "testing",
            "SECRET_KEY": self.secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "JWT_ACCESS_TOKEN_EXPIRES_MINUTES": self.jwt_access_token_expires_minutes,
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "pool_recycle": self.database_pool_recycle,
                "pool_size": self.database_pool_size,
                "max_overflow": self.database_max_overflow,
                "pool_timeout": self.database_pool_timeout,
            },
            "HOST": self.host,
            "PORT": self.port,
            "CORS_ORIGINS": self.cors_origins,
            "SOCKETIO_ASYNC_MODE": "threading",
            "SOCKETIO_MAX_HTTP_BUFFER_SIZE": self.socketio_max_http_buffer_size,
            "TYPING_TIMEOUT_SECONDS": self.typing_timeout_seconds,
            "NOTIFICATION_RETENTION_DAYS": self.notification_retention_days,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "SUPABASE_STORAGE_BUCKET": self.supabase_storage_bucket,
            "MAX_ATTACHMENT_SIZE_MB": self.max_attachment_size_mb,
            "MAX_TOTAL_ATTACHMENT_SIZE_MB": self.max_total_attachment_size_mb,
            "MAX_ATTACHMENTS_PER_MESSAGE": self.max_attachments_per_message,
            "ATTACHMENT_SIGNED_URL_EXPIRES_SECONDS": self.attachment_signed_url_expires_seconds,
            "RATE_LIMIT_ENABLED": self.rate_limit_enabled,
            "RATE_LIMIT_DEFAULT_REQUESTS": self.rate_limit_default_requests,
            "RATE_LIMIT_DEFAULT_WINDOW_SECONDS": self.rate_limit_default_window_seconds,
            "AUTH_RATE_LIMIT_REQUESTS": self.auth_rate_limit_requests,
            "AUTH_RATE_LIMIT_WINDOW_SECONDS": self.auth_rate_limit_window_seconds,
            "SOCKET_RATE_LIMIT_EVENTS": self.socket_rate_limit_events,
            "SOCKET_RATE_LIMIT_WINDOW_SECONDS": self.socket_rate_limit_window_seconds,
            "MAX_REQUEST_BODY_SIZE_BYTES": self.max_request_body_size_bytes,
            "MAX_QUERY_PARAMS": self.max_query_params,
            "MAX_HEADER_SIZE": self.max_header_size,
            "TRUST_PROXY": self.trust_proxy,
            "CORS_ALLOW_CREDENTIALS": self.cors_allow_credentials,
            "HSTS_ENABLED": self.hsts_enabled,
            "LOG_LEVEL": self.log_level,
            "LOG_FORMAT": self.log_format,
            "METRICS_ENABLED": self.metrics_enabled,
            "METRICS_ENDPOINT_ENABLED": self.metrics_endpoint_enabled,
            "SLOW_REQUEST_THRESHOLD_MS": self.slow_request_threshold_ms,
            "JWT_ALGORITHM": self.jwt_algorithm,
            "MAX_CONTENT_LENGTH": self.max_total_attachment_size_mb * 1024 * 1024 + 1024 * 1024,
        }

    def sanitized_summary(self) -> dict[str, object]:
        return {
            "environment": self.app_env,
            "database": "configured",
            "socketio": "enabled",
            "cors_origins": len(self.cors_origins) if isinstance(self.cors_origins, list) else 1,
            "metrics": "enabled" if self.metrics_enabled else "disabled",
            "rate_limiting": "enabled" if self.rate_limit_enabled else "disabled",
        }
