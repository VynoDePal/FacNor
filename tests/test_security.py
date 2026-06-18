from pathlib import Path

from app.main import get_jwt_secret


def test_jwt_secret_has_no_hardcoded_development_fallback(monkeypatch):
    monkeypatch.delenv("FACNOR_JWT_SECRET", raising=False)

    secret = get_jwt_secret()

    assert "change-me" not in secret
    assert len(secret) >= 32


def test_jwt_secret_uses_environment_when_configured(monkeypatch):
    monkeypatch.setenv("FACNOR_JWT_SECRET", "configured-secret-with-sufficient-length")

    assert get_jwt_secret() == "configured-secret-with-sufficient-length"


def test_frontend_dev_scripts_do_not_bind_all_interfaces():
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")
    all_interfaces_host = ".".join(["0", "0", "0", "0"])

    assert f"--host {all_interfaces_host}" not in package_json


def test_requirements_do_not_include_suspicious_httpx_typosquat():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "httpx2" not in requirements
