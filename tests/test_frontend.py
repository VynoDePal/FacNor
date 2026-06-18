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


def test_frontend_exposes_authenticated_client_crud_interface():
    api_source = Path("frontend/src/api.ts").read_text(encoding="utf-8")
    app_source = Path("frontend/src/main.tsx").read_text(encoding="utf-8")

    assert "Authorization: `Bearer ${token}`" in api_source
    assert "listClients" in api_source
    assert "createClient" in api_source
    assert "updateClient" in api_source
    assert "deleteClient" in api_source
    assert "'/clients'" in api_source
    assert "`/clients/${clientId}`" in api_source

    assert "Gestion des clients" in app_source
    assert "Créer un client" in app_source
    assert "Modifier le client" in app_source
    assert "Supprimer" in app_source
    assert "SIREN" in app_source
    assert "TVA intracommunautaire" in app_source


def test_frontend_exposes_invoice_creation_interface_with_dynamic_totals():
    api_source = Path("frontend/src/api.ts").read_text(encoding="utf-8")
    app_source = Path("frontend/src/main.tsx").read_text(encoding="utf-8")

    assert "InvoicePayload" in api_source
    assert "InvoiceLinePayload" in api_source
    assert "listInvoices" in api_source
    assert "createInvoice" in api_source
    assert "'/invoices'" in api_source

    assert "Création de factures" in app_source
    assert "Créer une facture" in app_source
    assert "Ajouter une ligne" in app_source
    assert "Total HT" in app_source
    assert "Total TVA" in app_source
    assert "Total TTC" in app_source
    assert "calculateInvoiceTotals" in app_source
    assert "createInvoice(token, buildPayload())" in app_source


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
