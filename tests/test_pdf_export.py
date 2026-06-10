import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.client import Client
from app.models.facture import Facture, LigneFacture
from sqlalchemy.orm import Session

def test_export_facture_pdf(client, db: Session):
    # 1. Create a client
    test_client = Client(
        nom="Client Test PDF",
        email="test-pdf@client.com",
        adresse="123 Rue des Tests, 75000 Paris",
        siat_siren="123456789",
        type_client="entreprise"
    )
    db.add(test_client)
    db.commit()
    db.refresh(test_client)

    # 2. Create a facture
    test_facture = Facture(
        numero="FAC-TEST-PDF-001",
        client_id=test_client.id,
        date_facture=pytest.importorskip("datetime").date.today(),
        statut="brouillon"
    )
    db.add(test_facture)
    db.commit()
    db.refresh(test_facture)

    # 3. Create lines for the facture
    line1 = LigneFacture(
        facture_id=test_facture.id,
        description="Service de Consulting",
        quantite=2,
        prix_unitaire_ht=100.0,
        taux_tva=20.0
    )
    line2 = LigneFacture(
        facture_id=test_facture.id,
        description="Installation Logiciel",
        quantite=1,
        prix_unitaire_ht=500.0,
        taux_tva=20.0
    )
    db.add_all([line1, line2])
    db.commit()

    # 4. Call the PDF export endpoint
    response = client.get(f"/factures/{test_facture.id}/pdf")

    # 5. Assertions
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.content) > 0
