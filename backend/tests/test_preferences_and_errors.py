def test_get_default_preferences(client, registered_user):
    resp = client.get("/preferences")
    assert resp.status_code == 200
    body = resp.json()
    assert body["price_threshold_pct"] == 2.0
    assert body["volume_spike_multiplier"] == 2.0


def test_update_preferences_partial(client, registered_user):
    resp = client.patch("/preferences", json={"price_threshold_pct": 5.0})
    assert resp.status_code == 200
    body = resp.json()
    assert body["price_threshold_pct"] == 5.0
    assert body["volume_spike_multiplier"] == 2.0  # untouched fields stay put


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={"email": "x@example.com", "password": "short"})
    assert resp.status_code == 422


def test_register_rejects_invalid_email(client):
    resp = client.post("/auth/register", json={"email": "not-an-email", "password": "LongEnough1"})
    assert resp.status_code == 422


def test_watchlist_requires_auth(client):
    resp = client.get("/watchlists")
    assert resp.status_code == 401


def test_change_story_requires_watchlist_id_param(client, registered_user):
    resp = client.get("/stocks/RELIANCE/change-story")
    assert resp.status_code == 422


def test_change_story_unknown_symbol_404(client, registered_user):
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    resp = client.get("/stocks/NOPE/change-story", params={"watchlist_id": wl["id"]})
    assert resp.status_code == 404


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_preferences_browser_navigation_serves_spa(client, tmp_path, monkeypatch):
    from app import main

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Market Pulse</title>")
    monkeypatch.setattr(main, "FRONTEND_DIR", dist)

    resp = client.get("/preferences", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Market Pulse" in resp.text
