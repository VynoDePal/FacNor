from pathlib import Path

import pytest

from app.main import get_jwt_secret


def test_jwt_secret_requires_secure_environment_configuration(monkeypatch):
    monkeypatch.delenv("FACNOR_JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="FACNOR_JWT_SECRET"):
        get_jwt_secret()


def test_jwt_secret_rejects_short_environment_value(monkeypatch):
    monkeypatch.setenv("FACNOR_JWT_SECRET", "short-secret")

    with pytest.raises(RuntimeError, match="at least 32"):
        get_jwt_secret()


def test_jwt_secret_uses_environment_when_configured(monkeypatch):
    monkeypatch.setenv("FACNOR_JWT_SECRET", "configured-secret-with-sufficient-length")

    assert get_jwt_secret() == "configured-secret-with-sufficient-length"


def test_frontend_does_not_persist_bearer_token_in_local_storage():
    app_source = Path("frontend/src/main.tsx").read_text(encoding="utf-8")

    assert "localStorage.setItem(TOKEN_STORAGE_KEY" not in app_source
    assert "sessionStorage.setItem(TOKEN_STORAGE_KEY" in app_source


def test_sqlite_connections_keep_default_thread_safety_guard():
    db_source = Path("app/db.py").read_text(encoding="utf-8")

    assert "check_same_thread=False" not in db_source


def test_frontend_dev_scripts_do_not_bind_all_interfaces():
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")
    all_interfaces_host = ".".join(["0", "0", "0", "0"])

    assert f"--host {all_interfaces_host}" not in package_json


def test_requirements_do_not_include_suspicious_httpx_typosquat():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "httpx2" not in requirements
