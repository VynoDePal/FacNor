from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str = "owner@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct-password"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_client_crud_for_authenticated_user(client: TestClient) -> None:
    headers = _auth_headers(client)
    create_response = client.post(
        "/clients",
        headers=headers,
        json={
            "name": "Dupont SAS",
            "client_type": "company",
            "email": "contact@example.com",
            "address": "1 rue de Paris, 75001 Paris",
            "siren": "732 829 320",
            "vat_number": "FR 44 732829320",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Dupont SAS"
    assert created["siren"] == "732829320"
    assert created["vat_number"] == "FR44732829320"

    list_response = client.get("/clients", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    get_response = client.get(f"/clients/{created['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "contact@example.com"

    update_response = client.put(
        f"/clients/{created['id']}",
        headers=headers,
        json={"name": "Jean Dupont", "client_type": "individual"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Jean Dupont"
    assert updated["client_type"] == "individual"
    assert updated["siren"] is None
    assert updated["vat_number"] is None

    delete_response = client.delete(f"/clients/{created['id']}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/clients/{created['id']}", headers=headers).status_code == 404


def test_clients_are_scoped_to_current_user(client: TestClient) -> None:
    first_headers = _auth_headers(client, "first@example.com")
    second_headers = _auth_headers(client, "second@example.com")

    create_response = client.post(
        "/clients",
        headers=first_headers,
        json={"name": "Client privé", "client_type": "individual"},
    )
    assert create_response.status_code == 201
    client_id = create_response.json()["id"]

    assert client.get("/clients", headers=second_headers).json() == []
    assert client.get(f"/clients/{client_id}", headers=second_headers).status_code == 404
    assert client.delete(f"/clients/{client_id}", headers=second_headers).status_code == 404


def test_company_client_requires_valid_siren_and_vat(client: TestClient) -> None:
    headers = _auth_headers(client)

    missing_response = client.post(
        "/clients",
        headers=headers,
        json={"name": "Entreprise", "client_type": "company"},
    )
    invalid_siren_response = client.post(
        "/clients",
        headers=headers,
        json={
            "name": "Entreprise",
            "client_type": "company",
            "siren": "123456789",
            "vat_number": "FR12123456789",
        },
    )
    mismatched_vat_response = client.post(
        "/clients",
        headers=headers,
        json={
            "name": "Entreprise",
            "client_type": "company",
            "siren": "732829320",
            "vat_number": "FR96439352666",
        },
    )

    assert missing_response.status_code == 422
    assert invalid_siren_response.status_code == 422
    assert mismatched_vat_response.status_code == 422


def test_client_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/clients").status_code == 401
    assert client.post("/clients", json={"name": "Test", "client_type": "individual"}).status_code == 401
