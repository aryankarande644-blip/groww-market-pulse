from app.models import Instrument


def _add_instrument(db_session, symbol, base_price=500.0):
    inst = Instrument(symbol=symbol, name=symbol.title(), exchange="NSE", sector="Test", base_price=base_price)
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


def test_stale_symbol_flagged_and_never_silently_shown_as_live(client, registered_user, db_session):
    _add_instrument(db_session, "ITC", 468.90)  # ITC is scripted as "stale" in the mock provider
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "ITC"})

    resp = client.get(f"/watchlists/{wl['id']}/market-state")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["quote"]["quality"] == "STALE"
    assert item["quote"]["delayed"] is True
    assert item["quote"]["freshness_seconds"] > 600  # meaningfully old, not "just now"


def test_delayed_symbol_flagged(client, registered_user, db_session):
    _add_instrument(db_session, "MARUTI", 12480.0)  # scripted as "delayed"
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "MARUTI"})
    # advance to step 1 so the delayed scenario's market_timestamp lag applies
    client.post(f"/watchlists/{wl['id']}/simulate")

    resp = client.get(f"/watchlists/{wl['id']}/market-state")
    item = resp.json()["items"][0]
    assert item["quote"]["quality"] == "DELAYED"
    assert item["quote"]["delayed"] is True


def test_change_story_surfaces_stale_caveat_in_reasons(client, registered_user, db_session):
    _add_instrument(db_session, "ITC", 468.90)
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "ITC"})
    client.get(f"/watchlists/{wl['id']}/attention-summary")

    story = client.get("/stocks/ITC/change-story", params={"watchlist_id": wl["id"]})
    assert story.status_code == 200
    reasons = " ".join(story.json()["attention"]["reasons"]).lower()
    assert "stale" in reasons
