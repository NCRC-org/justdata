"""Behind Cloud Run, redirects must keep the https scheme (ProxyFix in create_app)."""


def test_redirect_keeps_forwarded_https_scheme():
    from justdata.main.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as s:
        s["user_type"] = "admin"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    resp = client.get("/analytics", headers={"X-Forwarded-Proto": "https"})
    assert resp.status_code == 308
    assert resp.headers["Location"].startswith("https://"), resp.headers["Location"]
