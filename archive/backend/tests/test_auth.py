"""Tests for authentication flows: registration, login, token refresh, validation."""
from tests.conftest import make_user, auth_headers


class TestRegistration:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "strongpass1",
            "name": "New User",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "new@example.com"
        assert data["user"]["name"] == "New User"
        # Cookies should be set
        assert "access_token" in resp.cookies

    def test_register_duplicate_email(self, client, db_session):
        make_user(db_session, email="dup@example.com")
        resp = client.post("/api/auth/register", json={
            "email": "dup@example.com",
            "password": "strongpass1",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "short@example.com",
            "password": "short",
        })
        assert resp.status_code == 422  # Pydantic validation

    def test_register_invalid_email(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "strongpass1",
        })
        assert resp.status_code == 422

    def test_register_empty_body(self, client):
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, db_session):
        make_user(db_session, email="login@example.com", password="mypassword1")
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "mypassword1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "login@example.com"
        assert "access_token" in resp.cookies

    def test_login_wrong_password(self, client, db_session):
        make_user(db_session, email="wrong@example.com", password="rightpass1")
        resp = client.post("/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass1",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "ghost@example.com",
            "password": "whatever1",
        })
        assert resp.status_code == 401


class TestTokenRefresh:
    def test_refresh_via_cookie(self, client, db_session):
        make_user(db_session, email="refresh@example.com", password="mypassword1")
        # Login to get cookies
        login_resp = client.post("/api/auth/login", json={
            "email": "refresh@example.com",
            "password": "mypassword1",
        })
        assert login_resp.status_code == 200

        # Refresh using cookies — send no body so TokenRefresh defaults to None
        refresh_resp = client.post("/api/auth/refresh")
        assert refresh_resp.status_code == 200
        assert refresh_resp.json()["user"]["email"] == "refresh@example.com"


class TestCurrentUser:
    def test_me_authenticated(self, client, db_session):
        user = make_user(db_session, email="me@example.com")
        resp = client.get("/api/auth/me", headers=auth_headers(user))
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@example.com"

    def test_me_no_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401
