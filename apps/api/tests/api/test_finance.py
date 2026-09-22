from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers, register_user


def _org_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/organizations", headers=headers).json()[0]["id"]


def _create_customer(client: TestClient, org_id: str, headers: dict) -> dict:
    response = client.post(
        f"/api/v1/organizations/{org_id}/customers",
        json={"name": "Carlos Souza"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_order(client: TestClient, org_id: str, headers: dict, customer_id: str) -> dict:
    response = client.post(
        f"/api/v1/organizations/{org_id}/orders",
        json={"customer_id": customer_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_list_transactions(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "despesa", "category": "energia", "amount": 150.0, "mark_as_paid": True},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    transaction = response.json()
    assert transaction["paid_at"] is not None

    response = client.get(f"/api/v1/organizations/{org_id}/finance/transactions", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_unpaid_transaction_can_be_marked_paid(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    transaction = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "custo", "category": "material", "amount": 80.0},
        headers=headers,
    ).json()
    assert transaction["paid_at"] is None

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions/{transaction['id']}/mark-paid",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["paid_at"] is not None


def test_rejects_invalid_transaction_type(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "bonus", "category": "x", "amount": 10.0},
        headers=headers,
    )
    assert response.status_code == 422


def test_transaction_can_reference_a_valid_order(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = _create_order(client, org_id, headers, customer["id"])

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={
            "type": "receita",
            "category": "pedido",
            "amount": 200.0,
            "reference_order_id": order["id"],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["reference_order_id"] == order["id"]


def test_transaction_rejects_unknown_order(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={
            "type": "receita",
            "category": "pedido",
            "amount": 200.0,
            "reference_order_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_financial_summary_computes_profit(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)

    client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "receita", "category": "venda", "amount": 1000.0, "mark_as_paid": True},
        headers=headers,
    )
    client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "custo", "category": "material", "amount": 300.0, "mark_as_paid": True},
        headers=headers,
    )
    client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "despesa", "category": "marketing", "amount": 100.0},
        headers=headers,
    )

    response = client.get(f"/api/v1/organizations/{org_id}/finance/summary", headers=headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_revenue"] == 1000.0
    assert summary["total_cost"] == 300.0
    assert summary["total_expense"] == 100.0
    assert summary["profit"] == 600.0
    assert summary["pending_payables"] == 100.0
    assert summary["pending_receivables"] == 0.0


def test_marking_order_as_paid_creates_a_revenue_transaction(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, headers)
    customer = _create_customer(client, org_id, headers)
    order = _create_order(client, org_id, headers, customer["id"])
    client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/items",
        json={"quantity": 1, "unit_price": 250.0},
        headers=headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/orders/{order['id']}/transition",
        json={"status": "paid"},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    transactions = client.get(
        f"/api/v1/organizations/{org_id}/finance/transactions", headers=headers
    ).json()
    assert len(transactions) == 1
    assert transactions[0]["type"] == "receita"
    assert transactions[0]["amount"] == 250.0
    assert transactions[0]["reference_order_id"] == order["id"]
    assert transactions[0]["paid_at"] is not None

    summary = client.get(
        f"/api/v1/organizations/{org_id}/finance/summary", headers=headers
    ).json()
    assert summary["total_revenue"] == 250.0
    assert summary["pending_receivables"] == 0.0


def test_viewer_cannot_create_transaction(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    viewer = register_user(client, organization_name="Solo Org", email="viewer@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "viewer@acme.io", "role": "VIEWER"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "receita", "category": "venda", "amount": 100.0},
        headers=auth_headers(viewer["access_token"]),
    )
    assert response.status_code == 403


def test_operator_cannot_create_transaction_only_manager_can(client: TestClient):
    owner = register_user(client, organization_name="Acme Prints", email="owner@acme.io")
    owner_headers = auth_headers(owner["access_token"])
    org_id = _org_id(client, owner_headers)

    operator = register_user(client, organization_name="Solo Org 2", email="operator@acme.io")
    client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"email": "operator@acme.io", "role": "OPERATOR"},
        headers=owner_headers,
    )

    response = client.post(
        f"/api/v1/organizations/{org_id}/finance/transactions",
        json={"type": "receita", "category": "venda", "amount": 100.0},
        headers=auth_headers(operator["access_token"]),
    )
    assert response.status_code == 403
