"""Tests for the auth API blueprint: signup, signin, and the token_required decorator.

UserService DB interactions are mocked for signup/signin tests.  The
``token_required`` decorator is tested by sending requests to a protected
endpoint (collections list).
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.tests.conftest import SAMPLE_USER_PAYLOAD, SAMPLE_GUEST_SESSION_ID


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JSON_HEADERS = {"Content-Type": "application/json"}


# ── /signup ──────────────────────────────────────────────────────────────

class TestSignup:
    """Tests for POST /api/auth/signup."""

    @patch("app.api.auth.UserService")
    @patch("app.api.auth.validate_email")
    def test_successful_signup(self, mock_validate, mock_svc_cls, client):
        """Valid email + 6-char password creates a user and returns 200."""
        mock_valid = MagicMock()
        mock_valid.email = "user@example.com"
        mock_validate.return_value = mock_valid

        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "user@example.com",
                                            "password": "abcdef"}))
        assert resp.status_code == 200
        assert b"user created" in resp.data

    def test_missing_email(self, client):
        """Missing email returns 401."""
        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"password": "abcdef"}))
        assert resp.status_code == 401

    def test_missing_password(self, client):
        """Missing password returns 401."""
        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "a@b.com"}))
        assert resp.status_code == 401

    def test_empty_body(self, client):
        """An empty body returns 401."""
        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({}))
        assert resp.status_code == 401

    @patch("app.api.auth.validate_email")
    def test_invalid_email(self, mock_validate, client):
        """An invalid email returns 401."""
        from email_validator import EmailNotValidError
        mock_validate.side_effect = EmailNotValidError("bad")
        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "not-an-email",
                                            "password": "abcdef"}))
        assert resp.status_code == 401

    @patch("app.api.auth.validate_email")
    def test_password_wrong_length(self, mock_validate, client):
        """Password that is not exactly 6 chars returns 401."""
        mock_valid = MagicMock()
        mock_valid.email = "u@b.com"
        mock_validate.return_value = mock_valid

        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "u@b.com",
                                            "password": "short"}))
        assert resp.status_code == 401
        assert b"password length" in resp.data

    @patch("app.api.auth.validate_email")
    def test_password_too_long(self, mock_validate, client):
        """Password longer than 6 chars returns 401."""
        mock_valid = MagicMock()
        mock_valid.email = "u@b.com"
        mock_validate.return_value = mock_valid

        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "u@b.com",
                                            "password": "toolong1"}))
        assert resp.status_code == 401

    def test_whitespace_only_email(self, client):
        """An all-whitespace email returns 401."""
        resp = client.post("/api/auth/signup", headers=JSON_HEADERS,
                           data=json.dumps({"email": "   ",
                                            "password": "abcdef"}))
        assert resp.status_code == 401


# ── /signin ──────────────────────────────────────────────────────────────

class TestSignin:
    """Tests for POST /api/auth/signin."""

    @patch("app.api.auth.UserService")
    def test_successful_signin(self, mock_svc_cls, client):
        """Valid credentials return a token."""
        mock_svc = mock_svc_cls.return_value
        mock_svc.verify_user_pwd.return_value = "user-id-1"
        mock_svc.create_token.return_value = "jwt-token-abc"

        resp = client.post("/api/auth/signin", headers=JSON_HEADERS,
                           data=json.dumps({"email": "a@b.com",
                                            "password": "secret"}))
        assert resp.status_code == 200
        assert resp.get_json()["token"] == "jwt-token-abc"

    @patch("app.api.auth.UserService")
    def test_wrong_password(self, mock_svc_cls, client):
        """Invalid credentials return 401."""
        mock_svc = mock_svc_cls.return_value
        mock_svc.verify_user_pwd.return_value = None

        resp = client.post("/api/auth/signin", headers=JSON_HEADERS,
                           data=json.dumps({"email": "a@b.com",
                                            "password": "wrong"}))
        assert resp.status_code == 401

    def test_missing_fields(self, client):
        """Missing email or password returns 401."""
        resp = client.post("/api/auth/signin", headers=JSON_HEADERS,
                           data=json.dumps({"email": "a@b.com"}))
        assert resp.status_code == 401

    def test_empty_body(self, client):
        """No body returns 401."""
        resp = client.post("/api/auth/signin", headers=JSON_HEADERS,
                           data=json.dumps({}))
        assert resp.status_code == 401


# ── token_required decorator ─────────────────────────────────────────────

class TestTokenRequired:
    """Tests for the token_required decorator by hitting a protected route."""

    def test_no_headers_returns_401(self, client):
        """A request without Authorization or GuestUserSessionId returns 401."""
        resp = client.get("/api/collections")
        assert resp.status_code == 401

    def test_valid_token_passes(self, client, mock_auth, auth_headers):
        """A valid Authorization header (mocked) grants access."""
        resp = client.get("/api/collections", headers=auth_headers)
        assert resp.status_code == 200

    def test_guest_session_passes(self, client, mock_auth, guest_headers):
        """A GuestUserSessionId header grants access."""
        resp = client.get("/api/collections", headers=guest_headers)
        assert resp.status_code == 200

    @patch("app.api.auth.UserService")
    def test_invalid_token_returns_401(self, mock_svc_cls, client):
        """An invalid token (decode returns string) returns 401."""
        mock_svc_cls.return_value.decode_token.return_value = "Token expired"
        resp = client.get("/api/collections",
                          headers={"Authorization": "bad-token"})
        assert resp.status_code == 401

    @patch("app.api.auth.UserService")
    def test_decode_exception_returns_401(self, mock_svc_cls, client):
        """An exception during decode returns 401."""
        mock_svc_cls.return_value.decode_token.side_effect = Exception("boom")
        resp = client.get("/api/collections",
                          headers={"Authorization": "bad-token"})
        assert resp.status_code == 401
