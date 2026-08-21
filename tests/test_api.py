def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_list_sites(client):
    res = client.get("/sites")
    assert res.status_code == 200
    assert [s["code"] for s in res.json()] == ["TST-01"]


def test_get_site_404(client):
    assert client.get("/sites/999").status_code == 404


def test_list_items_paginates(client):
    res = client.get("/items", params={"limit": 2})
    body = res.json()
    assert res.status_code == 200
    assert body["total"] == 3
    assert len(body["results"]) == 2
    assert body["limit"] == 2


def test_filter_items_by_type(client):
    body = client.get("/items", params={"type": "meter"}).json()
    assert body["total"] == 1
    assert body["results"][0]["name"] == "Meter 1"


def test_create_item(client):
    site_id = client.get("/sites").json()[0]["id"]
    res = client.post(
        "/items",
        json={
            "name": "Transformer 9",
            "model_number": "PTX-480",
            "type": "transformer",
            "site_id": site_id,
        },
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Transformer 9"
    assert client.get("/items").json()["total"] == 4


def test_create_item_unknown_site_is_422(client):
    res = client.post(
        "/items",
        json={"name": "X", "model_number": "Y", "type": "z", "site_id": 4242},
    )
    assert res.status_code == 422


def test_create_item_validation_error_is_422(client):
    res = client.post("/items", json={"name": "", "model_number": "Y", "type": "z"})
    assert res.status_code == 422


def test_write_is_open_when_no_api_key_configured(client):
    """Demo posture: unset API_KEY leaves the write path open."""
    from app.config import settings

    assert not settings.api_key
    site_id = client.get("/sites").json()[0]["id"]
    res = client.post(
        "/items",
        json={"name": "Open", "model_number": "M", "type": "t", "site_id": site_id},
    )
    assert res.status_code == 201


def test_write_requires_key_once_configured(client, monkeypatch):
    """Setting API_KEY switches enforcement on with no code change."""
    from app.config import settings

    monkeypatch.setattr(settings, "api_key", "s3cret")
    site_id = client.get("/sites").json()[0]["id"]
    body = {"name": "Guarded", "model_number": "M", "type": "t", "site_id": site_id}

    assert client.post("/items", json=body).status_code == 401
    assert client.post("/items", json=body, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/items", json=body, headers={"X-API-Key": "s3cret"}).status_code == 201


def test_sql_injection_payload_is_treated_as_data(client):
    """Injection attempts are bound parameters, not SQL. The table survives."""
    evil = "'; DROP TABLE items; --"
    res = client.get("/items", params={"q": evil})
    assert res.status_code == 200
    assert res.json()["total"] == 0

    # The table is still there and still populated.
    assert client.get("/items").json()["total"] == 3


def test_items_by_site_report(client):
    body = client.get("/reports/items-by-site").json()
    counts = {(r["site_code"], r["type"]): r["count"] for r in body["rows"]}
    assert counts == {("TST-01", "inverter"): 2, ("TST-01", "meter"): 1}
    assert body["generated_at"]
