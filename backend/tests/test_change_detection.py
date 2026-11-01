def _make_watchlist_with_reliance(client):
    wl = client.post("/watchlists", json={"name": "My List"}).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"symbol": "RELIANCE"})
    return wl


def test_first_visit_creates_checkpoint_with_no_changes(client, registered_user, seeded_instrument):
    wl = _make_watchlist_with_reliance(client)
    resp = client.get(f"/watchlists/{wl['id']}/attention-summary")
    assert resp.status_code == 200
    body = resp.json()
    # First-ever visit: nothing to compare against yet, so nothing "changed".
    assert body["you_were_away"]["total_changed"] == 0


def test_simulate_creates_detectable_change_since_checkpoint(client, registered_user, seeded_instrument):
    wl = _make_watchlist_with_reliance(client)

    # Establish the baseline checkpoint (this is "10:14 AM").
    first = client.get(f"/watchlists/{wl['id']}/attention-summary")
    assert first.status_code == 200

    # Advance the mock market -- RELIANCE is configured as a scripted
    # "meaningful_up" scenario, so this must now show up as a real change.
    sim = client.post(f"/watchlists/{wl['id']}/simulate")
    assert sim.status_code == 200

    after = client.get(f"/watchlists/{wl['id']}/attention-summary")
    assert after.status_code == 200
    body = after.json()
    assert body["you_were_away"]["total_changed"] >= 1
    reliance = next(c for c in body["all_changes"] if c["symbol"] == "RELIANCE")
    assert reliance["attention_score"] > 0
    assert reliance["price_change_pct"] > 0
    assert len(reliance["reasons"]) > 0


def test_manual_checkpoint_resets_comparison_baseline(client, registered_user, seeded_instrument):
    wl = _make_watchlist_with_reliance(client)
    client.get(f"/watchlists/{wl['id']}/attention-summary")
    client.post(f"/watchlists/{wl['id']}/simulate")

    changed = client.get(f"/watchlists/{wl['id']}/attention-summary").json()
    assert changed["you_were_away"]["total_changed"] >= 1

    # Explicitly mark everything as seen.
    cp = client.post(f"/watchlists/{wl['id']}/checkpoint")
    assert cp.status_code == 201

    fresh = client.get(f"/watchlists/{wl['id']}/attention-summary").json()
    assert fresh["you_were_away"]["total_changed"] == 0


def test_change_story_includes_timeline_and_reasons(client, registered_user, seeded_instrument):
    wl = _make_watchlist_with_reliance(client)
    client.get(f"/watchlists/{wl['id']}/attention-summary")
    client.post(f"/watchlists/{wl['id']}/simulate")

    story = client.get(f"/stocks/RELIANCE/change-story", params={"watchlist_id": wl["id"]})
    assert story.status_code == 200
    body = story.json()
    assert body["symbol"] == "RELIANCE"
    assert body["attention"]["total_score"] >= 0
    assert isinstance(body["timeline"], list)
    assert body["timeline"][0]["label"] == "You checked"
    assert body["timeline"][-1]["label"] == "You returned"


def test_change_event_and_attention_score_are_persisted(client, registered_user, seeded_instrument, db_session):
    from app.models import ChangeEvent, AttentionScore

    wl = _make_watchlist_with_reliance(client)
    client.get(f"/watchlists/{wl['id']}/attention-summary")
    client.post(f"/watchlists/{wl['id']}/simulate")
    client.get(f"/watchlists/{wl['id']}/attention-summary")

    events = db_session.query(ChangeEvent).all()
    assert len(events) >= 1
    scores = db_session.query(AttentionScore).all()
    assert len(scores) == len(events)


def test_repeated_summary_calls_do_not_duplicate_change_events(client, registered_user, seeded_instrument, db_session):
    from app.models import ChangeEvent

    wl = _make_watchlist_with_reliance(client)
    client.get(f"/watchlists/{wl['id']}/attention-summary")
    client.post(f"/watchlists/{wl['id']}/simulate")

    client.get(f"/watchlists/{wl['id']}/attention-summary")
    count_after_first = db_session.query(ChangeEvent).count()
    client.get(f"/watchlists/{wl['id']}/attention-summary")
    count_after_second = db_session.query(ChangeEvent).count()

    assert count_after_first == count_after_second
