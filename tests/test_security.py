import os

import pytest

from app.config import Config, ConfigurationError
from app.security.headers import get_security_headers
from app.security.rate_limiter import normalize_ip


def test_ip_normalization_removes_port_and_normalizes_ipv4(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "false")
    assert normalize_ip("127.0.0.1:12345") == "127.0.0.1"
    assert normalize_ip("::ffff:127.0.0.1") == "127.0.0.1"


def test_security_config_includes_rate_limit_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "secret-key-1234567890")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret-key-1234567890")
    config = Config.from_environment()
    assert config.rate_limit_enabled is True
    assert config.rate_limit_default_requests == 120
    assert config.auth_rate_limit_requests == 10
    assert config.socket_rate_limit_events == 60


def test_security_headers_are_present_and_safe():
    headers = get_security_headers()
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_production_rejects_debug_and_missing_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db.example/realynk")
    monkeypatch.setenv("SECRET_KEY", "a-real-production-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "a-different-jwt-secret")
    with pytest.raises(ConfigurationError, match="DEBUG"):
        Config.from_environment()


def test_production_rejects_credentialed_wildcard_cors(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db.example/realynk")
    monkeypatch.setenv("SECRET_KEY", "a-real-production-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "a-different-jwt-secret")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    with pytest.raises(ConfigurationError, match="wildcard"):
        Config.from_environment()


def test_invalid_typed_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv("PORT", "65536")
    with pytest.raises(ConfigurationError, match="PORT"):
        Config.from_environment()

    monkeypatch.setenv("PORT", "5000")
    monkeypatch.setenv("RATE_LIMIT_DEFAULT_WINDOW_SECONDS", "0")
    with pytest.raises(ConfigurationError, match="RATE_LIMIT_DEFAULT_WINDOW_SECONDS"):
        Config.from_environment()
