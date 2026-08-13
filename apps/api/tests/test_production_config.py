import pytest
from pydantic import ValidationError
from app.core.config import Settings

def test_development_config_defaults():
    s = Settings(ENVIRONMENT="development")
    s.validate_production_rules()  # Should not raise

def test_production_config_rejects_default_secret_key():
    s = Settings(ENVIRONMENT="production", SECRET_KEY="pace-development-secret-key-change-in-production-32bytes")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        s.validate_production_rules()

def test_production_config_rejects_default_salt():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-key-at-least-32-bytes-long",
        INGESTION_KEY_SALT="pace-ingestion-salt-32bytes-secret"
    )
    with pytest.raises(ValueError, match="INGESTION_KEY_SALT"):
        s.validate_production_rules()

def test_production_config_rejects_demo_mode():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-key-at-least-32-bytes-long",
        INGESTION_KEY_SALT="secure-production-salt-at-least-32-bytes",
        DEMO_MODE=True
    )
    with pytest.raises(ValueError, match="DEMO_MODE"):
        s.validate_production_rules()

def test_production_config_rejects_wildcard_cors():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-key-at-least-32-bytes-long",
        INGESTION_KEY_SALT="secure-production-salt-at-least-32-bytes",
        DEMO_MODE=False,
        CORS_ORIGINS=["*"]
    )
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        s.validate_production_rules()

def test_valid_production_config():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="secure-production-key-at-least-32-bytes-long",
        INGESTION_KEY_SALT="secure-production-salt-at-least-32-bytes",
        DEMO_MODE=False,
        CORS_ORIGINS=["https://dashboard.pace.dev"]
    )
    s.validate_production_rules()  # Should succeed cleanly
