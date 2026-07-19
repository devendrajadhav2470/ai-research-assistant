"""Tests for collection access helpers and demo listing."""

import json

from app.extensions import db
from app.models.document import Collection
from app.services.collection_access import can_read_collection, can_write_collection
from app.tests.conftest import SAMPLE_USER_ID


JSON_CT = {"Content-Type": "application/json"}


class TestCollectionAccess:
    def test_owner_can_read_and_write(self, sample_collection):
        assert can_read_collection(sample_collection, SAMPLE_USER_ID)
        assert can_write_collection(sample_collection, SAMPLE_USER_ID)

    def test_other_user_denied(self, sample_collection):
        assert not can_read_collection(sample_collection, "other-user")
        assert not can_write_collection(sample_collection, "other-user")

    def test_demo_is_readable_not_writable(self, sample_user):
        demo = Collection(
            name="Demo Collection",
            description="shared",
            user_id=sample_user.id,
            is_demo=True,
        )
        db.session.add(demo)
        db.session.commit()
        assert can_read_collection(demo, "any-user-id")
        assert not can_write_collection(demo, "any-user-id")
        assert not can_write_collection(demo, sample_user.id)


class TestListIncludesDemo:
    def test_demo_appears_first(self, client, auth_headers, mock_auth, sample_user, sample_collection):
        demo = Collection(
            name="Demo Collection",
            description="shared",
            user_id=sample_user.id,
            is_demo=True,
        )
        db.session.add(demo)
        db.session.commit()

        resp = client.get("/api/collections", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data[0]["is_demo"] is True
        assert data[0]["name"] == "Demo Collection"
        assert any(c["name"] == "Test Collection" for c in data)

    def test_cannot_delete_demo(self, client, auth_headers, mock_auth, sample_user):
        demo = Collection(
            name="Demo Collection",
            description="shared",
            user_id=sample_user.id,
            is_demo=True,
        )
        db.session.add(demo)
        db.session.commit()

        resp = client.delete(f"/api/collections/{demo.id}", headers=auth_headers)
        assert resp.status_code == 403
