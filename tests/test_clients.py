from tests.test_api import auth_headers, register_user


VALID_SIREN = "732829320"
VALID_VAT = "FR44732829320"


def test_client_crud_for_b2c_client(client):
    user = register_user(client, "b2c@example.com")
    headers = auth_headers(user["access_token"])

    create_response = client.post(
        "/clients",
        headers=headers,
        json={"client_type": "b2c", "name": "Jean Dupont", "address": "3 rue A, Paris"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["client_type"] == "b2c"
    assert created["user_id"] == user["id"]

    list_response = client.get("/clients", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    get_response = client.get(f"/clients/{created['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Jean Dupont"

    update_response = client.put(
        f"/clients/{created['id']}",
        headers=headers,
        json={"name": "Jean Martin", "email": "jean.martin@example.com"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Jean Martin"
    assert update_response.json()["email"] == "jean.martin@example.com"

    delete_response = client.delete(f"/clients/{created['id']}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/clients/{created['id']}", headers=headers).status_code == 404


def test_create_b2b_client_requires_valid_siren_and_vat(client):
    user = register_user(client, "b2b@example.com")
    headers = auth_headers(user["access_token"])

    response = client.post(
        "/clients",
        headers=headers,
        json={
            "client_type": "b2b",
            "name": "Société Exemple",
            "address": "10 rue de la Paix, Paris",
            "siren": VALID_SIREN,
            "vat_number": VALID_VAT,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["siren"] == VALID_SIREN
    assert body["vat_number"] == VALID_VAT

    invalid_response = client.post(
        "/clients",
        headers=headers,
        json={
            "client_type": "b2b",
            "name": "Société Invalide",
            "address": "10 rue de la Paix, Paris",
            "siren": "123456789",
            "vat_number": "FR00123456789",
        },
    )
    assert invalid_response.status_code == 422


def test_update_client_to_b2b_validates_business_identifiers(client):
    user = register_user(client, "update-b2b@example.com")
    headers = auth_headers(user["access_token"])
    created = client.post("/clients", headers=headers, json={"name": "Prospect", "address": "1 rue A"}).json()

    invalid_response = client.put(
        f"/clients/{created['id']}",
        headers=headers,
        json={"client_type": "b2b", "siren": "123456789", "vat_number": "FR00123456789"},
    )
    assert invalid_response.status_code == 422

    valid_response = client.put(
        f"/clients/{created['id']}",
        headers=headers,
        json={"client_type": "b2b", "siren": VALID_SIREN, "vat_number": VALID_VAT},
    )
    assert valid_response.status_code == 200
    assert valid_response.json()["client_type"] == "b2b"


def test_clients_are_scoped_to_authenticated_owner(client):
    first_user = register_user(client, "client-owner@example.com")
    second_user = register_user(client, "client-other@example.com")
    first_headers = auth_headers(first_user["access_token"])
    second_headers = auth_headers(second_user["access_token"])

    created = client.post("/clients", headers=first_headers, json={"name": "Privé", "address": "1 rue A"})
    assert created.status_code == 201
    client_id = created.json()["id"]

    assert client.get(f"/clients/{client_id}", headers=second_headers).status_code == 404
    assert client.put(f"/clients/{client_id}", headers=second_headers, json={"name": "Vol"}).status_code == 404
    assert client.delete(f"/clients/{client_id}", headers=second_headers).status_code == 404
    assert client.get(f"/clients/{client_id}", headers=first_headers).status_code == 200
