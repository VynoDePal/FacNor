import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_frontend_package_declares_vite_scripts():
    package = json.loads((ROOT_DIR / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["dev"].startswith("vite")
    assert package["scripts"]["build"] == "tsc && vite build"
    declared = set(package["dependencies"]) | set(package.get("devDependencies", {}))
    assert {"vite", "typescript", "react", "react-dom"}.issubset(declared)


def test_frontend_calls_configurable_backend_api():
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in app_source
    assert "fetch(`${apiBaseUrl}/health`" in app_source
    assert "apiRequest<Client[]>('/clients')" in app_source
    assert "apiRequest<Client>('/clients'" in app_source
    assert "Authorization" in app_source


def test_frontend_exposes_client_and_invoice_management_interface():
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "Gestion des clients" in app_source
    assert "Créer le client" in app_source
    assert "SIREN" in app_source
    assert "Actualiser" in app_source
    assert "Gestion des factures" in app_source
    assert "Lignes de produits" in app_source
    assert "Créer la facture" in app_source
    assert "Montant TTC" in app_source
    assert "Marquer payée" in app_source


def test_frontend_updates_invoice_totals_dynamically():
    app_source = (ROOT_DIR / "src" / "App.tsx").read_text(encoding="utf-8")

    assert "useMemo" in app_source
    assert "invoicePreview" in app_source
    assert "Total TTC :" in app_source
    assert "formatMoney(invoicePreview.totalIncludingTax" in app_source
    assert "updateInvoiceLine(index, 'quantity'" in app_source
    assert "updateInvoiceLine(index, 'unit_price_excluding_tax'" in app_source
    assert "updateInvoiceLine(index, 'vat_rate'" in app_source


def test_frontend_entrypoint_is_wired_to_vite_html():
    html = (ROOT_DIR / "index.html").read_text(encoding="utf-8")
    main_source = (ROOT_DIR / "src" / "main.tsx").read_text(encoding="utf-8")

    assert 'src="/src/main.tsx"' in html
    assert "ReactDOM.createRoot" in main_source
