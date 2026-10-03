"""Tests for production security configuration."""

import importlib

import pytest


def _load_config(monkeypatch, **values):
    for key in ("ENVIRONMENT", "DEV_MODE", "JWT_SECRET"):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    import config

    return importlib.reload(config)


def test_production_requires_strong_jwt_secret(monkeypatch):
    config = _load_config(monkeypatch, ENVIRONMENT="production", JWT_SECRET="short")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        config.validate_settings()


def test_production_rejects_dev_mode(monkeypatch):
    config = _load_config(
        monkeypatch,
        ENVIRONMENT="production",
        JWT_SECRET="a" * 32,
        DEV_MODE="1",
    )

    with pytest.raises(RuntimeError, match="DEV_MODE"):
        config.validate_settings()


def test_production_accepts_secure_settings(monkeypatch):
    config = _load_config(
        monkeypatch,
        ENVIRONMENT="production",
        JWT_SECRET="a" * 32,
        DEV_MODE="0",
    )

    config.validate_settings()
