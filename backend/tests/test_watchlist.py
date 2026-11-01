def test_create_and_list_watchlist(client, registered_user):
    resp = client.post("/watchlists", json={"name": "Tech Stocks"})
    assert resp.status_code == 201
    wl_id = resp.json()["id"]

    listing = client.get("/watchlists")
    assert listing.status_code == 200
    names = [w["name"] for w in listing.json()]
    assert "Tech Stocks" in names


def test_add_and_remove_stock(client, registered_user, seeded_instrument):
    wl = client.post("/watchlists", json={"name": "My List"}).json()

    add = client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "RELIANCE"})
    assert add.status_code == 201

    dupe = client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "RELIANCE"})
    assert dupe.status_code == 409

    remove = client.delete(f"/watchlists/{wl['id']}/stocks/RELIANCE")
    assert remove.status_code == 204

    remove_again = client.delete(f"/watchlists/{wl['id']}/stocks/RELIANCE")
    assert remove_again.status_code == 404


def test_add_unknown_symbol_returns_404(client, registered_user):
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    resp = client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "NOPE"})
    assert resp.status_code == 404


def test_cannot_access_another_users_watchlist(client, registered_user, seeded_instrument, db_session):
    from app.auth import hash_password
    from app.models import User

    other = User(email="other@example.com", password_hash=hash_password("Whatever123"))
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    from app.models import Watchlist
    other_wl = Watchlist(user_id=other.id, name="Not Yours")
    db_session.add(other_wl)
    db_session.commit()
    db_session.refresh(other_wl)

    resp = client.get(f"/watchlists/{other_wl.id}/market-state")
    assert resp.status_code == 404


def test_market_state_bootstraps_snapshots(client, registered_user, seeded_instrument):
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "RELIANCE"})

    resp = client.get(f"/watchlists/{wl['id']}/market-state")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["symbol"] == "RELIANCE"
    assert body["items"][0]["quote"]["price"] > 0
