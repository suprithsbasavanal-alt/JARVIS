"""Unit Test Suite for Jarvis Centralized Configuration System."""

import os
import pytest
from config.settings import (
    JarvisSettings,
    EnvironmentMode,
    get_settings,
)
from config.constants import APP_NAME, APP_VERSION


def test_default_config_initialization():
    """Verifies default settings structure and constants."""
    settings = get_settings()
    assert settings.app_name == APP_NAME
    assert settings.app_version == APP_VERSION
    assert settings.environment == EnvironmentMode.DEVELOPMENT
    assert settings.debug is True


def test_environment_mode_helpers():
    """Verifies mode helper methods (is_development, is_production, is_testing)."""
    dev_settings = JarvisSettings(environment=EnvironmentMode.DEVELOPMENT, debug=True)
    assert dev_settings.is_development() is True
    assert dev_settings.is_production() is False

    prod_settings = JarvisSettings(environment=EnvironmentMode.PRODUCTION, debug=False)
    assert prod_settings.is_production() is True
    assert prod_settings.is_development() is False

    test_settings = JarvisSettings(environment=EnvironmentMode.TESTING, debug=False)
    assert test_settings.is_testing() is True


def test_feature_flags_helper():
    """Verifies feature flag query helper."""
    settings = JarvisSettings()
    assert settings.is_feature_enabled("enable_voice") is True
    assert settings.is_feature_enabled("enable_sandbox") is True
    assert settings.is_feature_enabled("non_existent_feature") is False


def test_database_dsn_computation():
    """Verifies PostgreSQL connection DSN string generator."""
    settings = JarvisSettings()
    dsn = settings.database.postgres_connection_string
    assert "postgresql+asyncpg://" in dsn
    assert "jarvis_user" in dsn
    assert "jarvis_db" in dsn


def test_custom_environment_overrides(monkeypatch):
    """Verifies environment variables dynamically override default configuration."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("FEATURES__ENABLE_VOICE", "false")
    monkeypatch.setenv("MODEL__DEFAULT_PROVIDER", "anthropic")

    custom_settings = JarvisSettings()
    assert custom_settings.environment == EnvironmentMode.PRODUCTION
    assert custom_settings.debug is False
    assert custom_settings.features.enable_voice is False
    assert custom_settings.model.default_provider == "anthropic"
