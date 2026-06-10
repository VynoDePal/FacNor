import pytest
from app.models.facture import Facture, LigneFacture
from app.models.client import Client
def test_ligne_facture_calculations():
    # Test simple calculation
    ligne = LigneFacture(
        description="Test Item",
        quantite=2,
        prix_unitaire_ht=100.0,
        taux_tva=20.0
    )
    assert ligne.montant_ht == 200.0
    assert ligne.montant_tva == 40.0
    assert ligne.montant_ttc == 240.0

    # Test with zero quantity
    ligne_zero = LigneFacture(
        description="Zero Item",
        quantite=0,
        prix_unitaire_ht=100.0,
        taux_tva=20.0
    )
    assert ligne_zero.montant_ht == 0.0
    assert ligne_zero.montant_tva == 0.0
    assert ligne_zero.montant_ttc == 0.0

    # Test with zero TVA
    ligne_no_tva = LigneFacture(
        description="No TVA Item",
        quantite=1,
        prix_unitaire_ht=100.0,
        taux_tva=0.0
    )
    assert ligne_no_tva.montant_ht == 100.0
    assert ligne_no_tva.montant_tva == 0.0
    assert ligne_no_tva.montant_ttc == 100.0

    # Test with different TVA rate
    ligne_low_tva = LigneFacture(
        description="Low TVA Item",
        quantite=1,
        prix_unitaire_ht=100.0,
        taux_tva=5.5
    )
    assert ligne_low_tva.montant_ht == 100.0
    assert ligne_low_tva.montant_tva == 5.5
    assert ligne_low_tva.montant_ttc == 105.5

def test_facture_totals(db):
    # Setup: we need a client for a facture
    client = Client(nom="Calc Client", type_client="particulier")
    db.add(client)
    db.commit()

    facture = Facture(
        numero="FAC-TEST-CALC",
        client_id=client.id,
        date_facture="2023-10-27"
    )
    
    # We can manually associate lines to the facture relationship
    ligne1 = LigneFacture(description="Item 1", quantite=2, prix_unitaire_ht=100.0, taux_tva=20.0) # 200 HT, 40 TVA, 240 TTC
    ligne2 = LigneFacture(description="Item 2", quantite=1, prix_unitaire_ht=50.0, taux_tva=10.0)   # 50 HT, 5 TVA, 55 TTC
    
    facture.lignes = [ligne1, ligne2]
    
    assert facture.total_ht == 250.0
    assert facture.total_tva == 45.0
    assert facture.total_ttc == 295.0

def test_facture_empty_totals(db):
    client = Client(nom="Empty Client", type_client="particulier")
    db.add(client)
    db.commit()

    facture = Facture(
        numero="FAC-TEST-EMPTY",
        client_id=client.id,
        date_facture="2023-10-27"
    )
    facture.lignes = []
    
    assert facture.total_ht == 0.0
    assert facture.total_tva == 0.0
    assert facture.total_ttc == 0.0
