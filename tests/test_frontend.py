import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_frontend_package_declares_vite_scripts():
    package = json.loads((ROOT_DIR / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["dev"].startswith("vite")
    assert package["scripts"]["build"] == "tsc && vite build"
    assert {"vite", "typescript", "react", "react-dom"}.issubset(package["dependencies"])


def test_frontend_calls_configurable_backend_api():
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in app_source
    assert "fetch(`${apiBaseUrl}/health`" in app_source


def test_frontend_entrypoint_is_wired_to_vite_html():
    html = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
    main_source = (ROOT_DIR / "src" / "main.tsx").read_text(encoding="utf-8")

    assert 'src="/src/main.tsx"' in html
    assert "ReactDOM.createRoot" in main_source
