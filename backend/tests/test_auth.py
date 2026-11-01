def test_register_creates_user_and_session_cookie(client):
    resp = client.post("/auth/register", json={
        "email": "new@example.com", "password": "GoodPassword1", "display_name": "New User",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "mp_session" in resp.cookies


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dupe@example.com", "password": "GoodPassword1"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_wrong_password_rejected(client, registered_user):
    resp = client.post("/auth/login", json={"email": "trader@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_success_and_me_endpoint(client, registered_user):
    resp = client.post("/auth/login", json={"email": "trader@example.com", "password": "SuperSecret123"})
    assert resp.status_code == 200
    me = client.get("/me")
    assert me.status_code == 200
    assert me.json()["email"] == "trader@example.com"


def test_me_requires_authentication(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_logout_revokes_session(client, registered_user):
    me_before = client.get("/me")
    assert me_before.status_code == 200

    logout = client.post("/auth/logout")
    assert logout.status_code == 204

    me_after = client.get("/me")
    assert me_after.status_code == 401
