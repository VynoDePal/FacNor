from pathlib import Path


def test_frontend_is_vite_project_with_required_scripts():
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")
    vite_config = Path("frontend/vite.config.ts").read_text(encoding="utf-8")

    assert '"dev"' in package_json
    assert '"build"' in package_json
    assert 'vite' in package_json
    assert '@vitejs/plugin-react' in package_json
    assert 'defineConfig' in vite_config


def test_frontend_uses_configurable_api_url_and_auth_endpoints():
    api_source = Path("frontend/src/api.ts").read_text(encoding="utf-8")
    app_source = Path("frontend/src/main.tsx").read_text(encoding="utf-8")

    assert "VITE_API_BASE_URL" in api_source
    assert "http://localhost:8000" in api_source
    assert "'/auth/login'" in api_source
    assert "'/users'" in api_source
    assert "facnor_access_token" in app_source
    assert "setView('dashboard')" in app_source
    assert "Tableau de bord" in app_source


def test_api_allows_configured_frontend_origin(client):
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
