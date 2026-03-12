"""Tests for the config API blueprint: GET /api/config/defaults."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture
def headers(auth_headers, mock_auth):
    """Auth-bypassed headers."""
    return auth_headers


class TestGetDefaults:
    """Tests for GET /api/config/defaults."""

    @patch.dict(os.environ, {
        "DEFAULT_MODEL_NAME": "gpt-4o",
        "DEFAULT_LLM_PROVIDER": "openai",
    })
    def test_returns_defaults(self, client, headers):
        """When env vars are set, defaults are returned."""
        resp = client.get("/api/config/defaults", headers=headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["default_model"] == "gpt-4o"
        assert body["default_model_provider"] == "openai"

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_model_returns_404(self, client, headers):
        """Returns 404 when DEFAULT_MODEL_NAME is not set."""
        os.environ.pop("DEFAULT_MODEL_NAME", None)
        os.environ.pop("DEFAULT_LLM_PROVIDER", None)
        resp = client.get("/api/config/defaults", headers=headers)
        assert resp.status_code == 404

    @patch.dict(os.environ, {"DEFAULT_MODEL_NAME": "gpt-4o"})
    def test_missing_provider_returns_404(self, client, headers):
        """Returns 404 when DEFAULT_LLM_PROVIDER is not set."""
        os.environ.pop("DEFAULT_LLM_PROVIDER", None)
        resp = client.get("/api/config/defaults", headers=headers)
        assert resp.status_code == 404
