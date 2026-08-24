"""Configuration contract.

The original hardcoded `user='root', password=''` and ran `debug=True`.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from itsc.config import ConfigError, ProductionConfig, get_config


def test_development_is_the_default():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FLASK_ENV", None)
        assert get_config().__class__.__name__ == "DevelopmentConfig"


def test_unknown_config_name_raises():
    with pytest.raises(ConfigError, match="Unknown config"):
        get_config("staging-typo")


@pytest.mark.parametrize("missing", ["SECRET_KEY", "DATABASE_URL", "REDIS_URL", "IP_HASH_PEPPER"])
def test_production_refuses_to_boot_without_each_secret(missing):
    env = {
        "SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql+psycopg://u:p@db/x",
        "REDIS_URL": "redis://redis:6379/0",
        "IP_HASH_PEPPER": "y" * 64,
    }
    env[missing] = ""
    with mock.patch.dict(os.environ, env, clear=False), pytest.raises(ConfigError) as exc:
        ProductionConfig()
    assert missing in str(exc.value)


def test_production_rejects_placeholder_secrets():
    env = {
        "SECRET_KEY": "change-me",
        "DATABASE_URL": "postgresql+psycopg://u:p@db/x",
        "REDIS_URL": "redis://redis:6379/0",
        "IP_HASH_PEPPER": "y" * 64,
    }
    with mock.patch.dict(os.environ, env, clear=False), pytest.raises(ConfigError):
        ProductionConfig()


def test_production_rejects_short_secret_key():
    env = {
        "SECRET_KEY": "short",
        "DATABASE_URL": "postgresql+psycopg://u:p@db/x",
        "REDIS_URL": "redis://redis:6379/0",
        "IP_HASH_PEPPER": "y" * 64,
    }
    with mock.patch.dict(os.environ, env, clear=False), pytest.raises(ConfigError, match="32"):
        ProductionConfig()


def test_production_refuses_debug():
    env = {
        "SECRET_KEY": "x" * 64,
        "DATABASE_URL": "postgresql+psycopg://u:p@db/x",
        "REDIS_URL": "redis://redis:6379/0",
        "IP_HASH_PEPPER": "y" * 64,
        "FLASK_DEBUG": "1",
    }
    with mock.patch.dict(os.environ, env, clear=False), pytest.raises(ConfigError, match="DEBUG"):
        ProductionConfig()


def test_production_never_enables_debug_or_insecure_cookies():
    assert ProductionConfig.DEBUG is False
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True


def test_no_credentials_are_hardcoded_in_source():
    """Regression for the module-level connection built with literal credentials.

    AST-based rather than a text search: a plain grep also matches *prose*
    describing the old vulnerability, so documenting the bug would fail the
    build for documenting it.
    """
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src"
    sensitive = {"password", "passwd", "pwd", "secret", "token", "api_key"}
    offenders = []

    for path in src.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg is None or keyword.arg.lower() not in sensitive:
                    continue
                # A literal string passed as a password= argument is the smell.
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    offenders.append(f"{path.name}:{node.lineno} {keyword.arg}=<literal>")
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"connect"}:
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        offenders.append(f"{path.name}:{node.lineno} connect(<literal>)")

    assert not offenders, "hardcoded credentials: " + "; ".join(offenders)
