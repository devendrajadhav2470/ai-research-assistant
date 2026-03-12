"""Tests for the UserService: user CRUD, JWT token management, and password verification.

Every method on UserService is exercised including happy-path, edge-case, and
exception scenarios.  All database interactions go through the in-memory SQLite
backend provided by conftest fixtures.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import bcrypt
import jwt
import pytest

from app.extensions import db
from app.models.user import User, Status
from app.services.user_service import UserService
from app.tests.conftest import SAMPLE_USER_EMAIL


# ---------------------------------------------------------------------------
# Fixtures local to this module
# ---------------------------------------------------------------------------

@pytest.fixture
def user_service():
    """A plain UserService instance (stateless)."""
    return UserService()


@pytest.fixture
def existing_user(app):
    """Insert a user whose password is known so we can test verification."""
    raw_password = "secret"
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        id=str(uuid.uuid4()),
        email="existing@example.com",
        password_hash=hashed,
        status=Status.ACTIVE,
        guest_user_session_id=str(uuid.uuid4()),
    )
    db.session.add(user)
    db.session.commit()
    return user, raw_password


# ── create_user ────────────────────────────────────────────────────────────

class TestCreateUser:
    """Tests for UserService.create_user."""

    def test_create_user_inserts_row(self, app, user_service):
        """A new user should be persisted to the database."""
        sid = str(uuid.uuid4())
        user_service.create_user(
            email="new@example.com",
            password="abcdef",
            guest_user_session_id=sid,
        )
        user = User.query.filter_by(email="new@example.com").first()
        assert user is not None
        assert user.email == "new@example.com"

    def test_create_user_hashes_password(self, app, user_service):
        """The stored password_hash must not equal the plaintext password."""
        sid = str(uuid.uuid4())
        user_service.create_user(email="hash@example.com", password="abcdef",
                                 guest_user_session_id=sid)
        user = User.query.filter_by(email="hash@example.com").first()
        assert user.password_hash != "abcdef"
        assert bcrypt.checkpw(b"abcdef", user.password_hash.encode("utf-8"))

    def test_create_user_with_guest_session(self, app, user_service):
        """guest_user_session_id should be stored when provided."""
        sid = str(uuid.uuid4())
        user_service.create_user(email="guest@example.com", password="abcdef",
                                 guest_user_session_id=sid)
        user = User.query.filter_by(email="guest@example.com").first()
        assert user.guest_user_session_id == sid


# ── get_user_from_email ───────────────────────────────────────────────────

class TestGetUserFromEmail:
    """Tests for UserService.get_user_from_email."""

    def test_returns_user_when_found(self, app, existing_user, user_service):
        """Return the User object for a known email."""
        user, _ = existing_user
        found = user_service.get_user_from_email(user.email)
        assert found.id == user.id

    def test_raises_when_not_found(self, app, user_service):
        """An IndexError is raised when no user matches the email."""
        with pytest.raises(IndexError):
            user_service.get_user_from_email("nobody@example.com")


# ── get_guest_user ─────────────────────────────────────────────────────────

class TestGetGuestUser:
    """Tests for UserService.get_guest_user."""

    def test_returns_existing_guest(self, app, user_service):
        """If a guest user already exists, return them without creating a new one."""
        sid = str(uuid.uuid4())
        user_service.create_user(
            email=f"guest_user_{sid}@temporary.com",
            password="password",
            guest_user_session_id=sid,
        )
        guest = user_service.get_guest_user(sid)
        assert guest.guest_user_session_id == sid

    def test_creates_guest_when_not_found(self, app, user_service):
        """A brand-new guest user is created when the session id is unknown."""
        new_sid = str(uuid.uuid4())
        guest = user_service.get_guest_user(new_sid)
        assert guest is not None
        assert guest.guest_user_session_id == new_sid


# ── create_token / decode_token ────────────────────────────────────────────

class TestTokenManagement:
    """Tests for JWT create_token and decode_token."""

    def test_create_token_returns_string(self, user_service):
        """create_token should return a non-empty JWT string."""
        token = user_service.create_token({"email": "a@b.com", "id": "1"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self, user_service):
        """decode_token should roundtrip a valid token back to a dict."""
        payload = {"email": "a@b.com", "id": "1"}
        token = user_service.create_token(dict(payload))
        decoded = user_service.decode_token(token)
        assert isinstance(decoded, dict)
        assert decoded["email"] == "a@b.com"

    def test_decode_expired_token(self, user_service):
        """An expired token should return an error string."""
        secret = "temporary_secret_key"
        expired_payload = {
            "email": "a@b.com",
            "id": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(expired_payload, secret, algorithm="HS256")
        result = user_service.decode_token(token)
        assert isinstance(result, str)
        assert "expired" in result.lower()

    def test_decode_invalid_token(self, user_service):
        """A tampered/invalid token should return an error string."""
        result = user_service.decode_token("not.a.valid.jwt")
        assert isinstance(result, str)

    def test_decode_wrong_secret(self, user_service):
        """A token signed with the wrong secret should fail decoding."""
        token = jwt.encode({"email": "x"}, "wrong-secret", algorithm="HS256")
        result = user_service.decode_token(token)
        assert isinstance(result, str)


# ── verify_user_pwd ───────────────────────────────────────────────────────

class TestVerifyUserPwd:
    """Tests for UserService.verify_user_pwd."""

    def test_correct_password_returns_user_id(self, app, existing_user, user_service):
        """Correct password returns the user's id."""
        user, raw_pw = existing_user
        result = user_service.verify_user_pwd(password=raw_pw, email=user.email)
        assert result == user.id

    def test_wrong_password_returns_none(self, app, existing_user, user_service):
        """Wrong password returns None."""
        user, _ = existing_user
        result = user_service.verify_user_pwd(password="wrongpwd", email=user.email)
        assert result is None

    def test_no_identifier_returns_none(self, app, user_service):
        """Calling without user_id or email returns None."""
        result = user_service.verify_user_pwd(password="anything")
        assert result is None

    def test_nonexistent_email_raises(self, app, user_service):
        """Verifying against an email with no matching user raises IndexError."""
        with pytest.raises(IndexError):
            user_service.verify_user_pwd(password="x", email="ghost@example.com")
