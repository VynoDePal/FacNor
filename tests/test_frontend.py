import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def test_frontend_package_defines_vite_scripts_and_dependencies() -> None:
    package = json.loads((ROOT_DIR / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["dev"] == "vite"
    assert "vite build" in package["scripts"]["build"]
    assert "tsc" in package["scripts"]["build"]
    declared_dependencies = package["dependencies"] | package["devDependencies"]

    assert {"vite", "typescript", "react", "react-dom", "@vitejs/plugin-react"}.issubset(
        declared_dependencies
    )


def test_frontend_uses_configurable_backend_base_url() -> None:
    api_source = (ROOT_DIR / "src" / "api.ts").read_text(encoding="utf-8")
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in api_source
    assert "http://localhost:8000" in api_source
    assert "fetch(`${getApiBaseUrl()}/health`)" in api_source
    assert "fetchHealth" in app_source


def test_frontend_entrypoint_mounts_react_application() -> None:
    index_html = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
    main_source = (ROOT_DIR / "src" / "main.tsx").read_text(encoding="utf-8")

    assert '<div id="root"></div>' in index_html
    assert 'src="/src/main.tsx"' in index_html
    assert "ReactDOM.createRoot" in main_source
    assert "<App />" in main_source


def test_frontend_authentication_ui_calls_login_and_shows_dashboard() -> None:
    api_source = (ROOT_DIR / "src" / "api.ts").read_text(encoding="utf-8")
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "fetch(`${getApiBaseUrl()}/auth/login`" in api_source
    assert "method: 'POST'" in api_source
    assert "facnor_access_token" in app_source
    assert "Connexion utilisateur" in app_source
    assert "type=\"email\"" in app_source
    assert "type=\"password\"" in app_source
    assert "setView('dashboard')" in app_source
    assert "Tableau de bord" in app_source


def test_frontend_client_management_ui_calls_clients_api() -> None:
    api_source = (ROOT_DIR / "src" / "api.ts").read_text(encoding="utf-8")
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "export async function fetchClients" in api_source
    assert "fetch(`${getApiBaseUrl()}${path}`" in api_source
    assert "'/clients'" in api_source
    assert "method: 'POST'" in api_source
    assert "method: 'PUT'" in api_source
    assert "Authorization: `Bearer ${token}`" in api_source
    assert "Gestion des clients" in app_source
    assert "Liste des clients" in app_source
    assert "Créer le client" in app_source
    assert "Modifier le client" in app_source
    assert "fetchClients(accessToken)" in app_source
    assert "createClient(accessToken, payload)" in app_source
    assert "updateClient(accessToken, editingClientId, payload)" in app_source
