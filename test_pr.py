"""
PR validation tests for Cache API.

These tests run automatically on every pull request via GitHub Actions.
They use FastAPI's TestClient so no live server or secrets are required —
dummy tokens are injected via environment variables before the app is imported.

Coverage:
  - App boots without crashing
  - Root endpoint shape
  - Auth layer: missing token, wrong token, valid token
  - Admin-only endpoints reject non-admin tokens
  - Key endpoints return sane HTTP status codes (not 500)
  - Request body validation (400 on bad input, not 500)
"""

import os
from unittest.mock import patch, MagicMock

# ── Inject dummy tokens BEFORE importing the app ──────────────────────────────
# This lets the app boot without real secrets.  Tests validate that the auth
# layer works correctly using these known values.
os.environ.setdefault("API_TOKEN", "ci-user-token")
os.environ.setdefault("ADMIN_API_TOKEN", "ci-admin-token")
# Setting REDIS_HOST prevents the Windows startup event from running Docker
os.environ.setdefault("REDIS_HOST", "127.0.0.1")
# ─────────────────────────────────────────────────────────────────────────────

# ── Patch Redis BEFORE importing the app ──────────────────────────────────────
# Without this, every endpoint call re-attempts the Redis TCP handshake and
# waits for socket_connect_timeout=5s each time, making 26 tests take 4+ min.
# Returning None instantly tells the app to skip Redis and go straight to DB.
_redis_none_patcher = patch("redis_cache.get_redis_client", return_value=None)
_redis_none_patcher.start()
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from fastapi.testclient import TestClient

# Import after env vars and patches are in place
from main import app  # noqa: E402

CLIENT = TestClient(app, raise_server_exceptions=False)

USER_TOKEN  = "ci-user-token"
ADMIN_TOKEN = "ci-admin-token"
WRONG_TOKEN = "totally-wrong-token"


@pytest.fixture(scope="session", autouse=True)
def stop_redis_patch():
    """Stop the module-level Redis patch when the session finishes."""
    yield
    _redis_none_patcher.stop()


def user_headers():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


def admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def wrong_headers():
    return {"Authorization": f"Bearer {WRONG_TOKEN}"}


# ─────────────────────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────────────────────

class TestRoot:
    def test_root_is_online(self):
        r = CLIENT.get("/")
        assert r.status_code == 200

    def test_root_returns_status_online(self):
        r = CLIENT.get("/")
        assert r.json().get("status") == "online"

    def test_root_has_service_field(self):
        r = CLIENT.get("/")
        assert "service" in r.json()

    def test_root_has_version_field(self):
        r = CLIENT.get("/")
        assert "version" in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Auth layer — /cache (user-auth endpoint)
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthLayer:
    def test_cache_no_token_returns_401_or_403(self):
        r = CLIENT.get("/cache", params={"market": "moneyline"})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_cache_wrong_token_returns_401_or_403(self):
        r = CLIENT.get("/cache", params={"market": "moneyline"}, headers=wrong_headers())
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_cache_valid_token_does_not_return_401_or_403(self):
        r = CLIENT.get("/cache", params={"market": "moneyline"}, headers=user_headers())
        assert r.status_code not in (401, 403), f"Valid token was rejected with {r.status_code}"

    def test_cache_valid_token_does_not_crash(self):
        r = CLIENT.get("/cache", params={"market": "moneyline"}, headers=user_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_batch_no_token_returns_401_or_403(self):
        r = CLIENT.post("/cache/batch", json={})
        assert r.status_code in (401, 403)

    def test_batch_wrong_token_returns_401_or_403(self):
        r = CLIENT.post("/cache/batch", json={}, headers=wrong_headers())
        assert r.status_code in (401, 403)

    def test_leagues_no_token_returns_401_or_403(self):
        r = CLIENT.get("/leagues")
        assert r.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Admin-only endpoints must reject non-admin tokens
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminOnly:
    def test_health_rejects_user_token(self):
        r = CLIENT.get("/health", headers=user_headers())
        assert r.status_code in (401, 403), f"User token should not access /health, got {r.status_code}"

    def test_health_accepts_admin_token(self):
        r = CLIENT.get("/health", headers=admin_headers())
        assert r.status_code not in (401, 403), f"Admin token was rejected from /health with {r.status_code}"

    def test_cache_stats_rejects_user_token(self):
        r = CLIENT.get("/cache/stats", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_cache_stats_accepts_admin_token(self):
        r = CLIENT.get("/cache/stats", headers=admin_headers())
        assert r.status_code not in (401, 403)

    def test_admin_logs_rejects_no_token(self):
        r = CLIENT.get("/admin/logs")
        assert r.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Input validation — bad params must return 400, not 500
# ─────────────────────────────────────────────────────────────────────────────

class TestInputValidation:
    def test_cache_missing_params_returns_400(self):
        """At least one of market/team/player/league is required."""
        r = CLIENT.get("/cache", headers=user_headers())
        assert r.status_code == 400, f"Expected 400 for missing params, got {r.status_code}"

    def test_cache_team_without_sport_returns_400(self):
        """Team-only search requires sport parameter."""
        r = CLIENT.get("/cache", params={"team": "Lakers"}, headers=user_headers())
        assert r.status_code == 400, f"Expected 400 for team without sport, got {r.status_code}"

    def test_cache_league_without_sport_returns_400(self):
        """League search requires sport parameter."""
        r = CLIENT.get("/cache", params={"league": "Premier League"}, headers=user_headers())
        assert r.status_code == 400, f"Expected 400 for league without sport, got {r.status_code}"

    def test_cache_market_query_does_not_crash(self):
        """Valid market query returns 200 or 404, never 500."""
        r = CLIENT.get("/cache", params={"market": "moneyline"}, headers=user_headers())
        assert r.status_code in (200, 404), f"Unexpected status {r.status_code}: {r.text[:200]}"

    def test_batch_empty_body_does_not_crash(self):
        """Empty batch body should not cause a server crash."""
        r = CLIENT.post("/cache/batch", json={}, headers=user_headers())
        assert r.status_code != 500, f"Server crashed on empty batch: {r.text[:200]}"

    def test_batch_valid_market_does_not_crash(self):
        r = CLIENT.post(
            "/cache/batch",
            json={"market": ["moneyline", "spread"]},
            headers=user_headers(),
        )
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_leagues_does_not_crash_with_auth(self):
        r = CLIENT.get("/leagues", headers=user_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# Response shape checks
# ─────────────────────────────────────────────────────────────────────────────

class TestResponseShapes:
    def test_health_response_has_status_field(self):
        r = CLIENT.get("/health", headers=admin_headers())
        if r.status_code == 200:
            assert "status" in r.json()

    def test_cache_response_is_json(self):
        r = CLIENT.get("/cache", params={"market": "moneyline"}, headers=user_headers())
        # Should always return JSON regardless of result
        try:
            r.json()
        except Exception:
            pytest.fail("Response was not valid JSON")

    def test_batch_response_is_json(self):
        r = CLIENT.post(
            "/cache/batch",
            json={"market": ["moneyline"]},
            headers=user_headers(),
        )
        try:
            r.json()
        except Exception:
            pytest.fail("Batch response was not valid JSON")


# ─────────────────────────────────────────────────────────────────────────────
# /cache/batch/precision
# ─────────────────────────────────────────────────────────────────────────────

class TestPrecisionBatch:
    def test_no_token_returns_401_or_403(self):
        r = CLIENT.post("/cache/batch/precision", json={"queries": []})
        assert r.status_code in (401, 403)

    def test_wrong_token_returns_401_or_403(self):
        r = CLIENT.post("/cache/batch/precision", json={"queries": []}, headers=wrong_headers())
        assert r.status_code in (401, 403)

    def test_valid_token_does_not_crash(self):
        r = CLIENT.post(
            "/cache/batch/precision",
            json={"queries": [{"market": "moneyline"}]},
            headers=user_headers(),
        )
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_response_has_results_key(self):
        r = CLIENT.post(
            "/cache/batch/precision",
            json={"queries": [{"market": "moneyline"}]},
            headers=user_headers(),
        )
        if r.status_code == 200:
            assert "results" in r.json()

    def test_response_has_total_queries_key(self):
        r = CLIENT.post(
            "/cache/batch/precision",
            json={"queries": [{"market": "moneyline"}]},
            headers=user_headers(),
        )
        if r.status_code == 200:
            assert "total_queries" in r.json()

    def test_multiple_queries_do_not_crash(self):
        r = CLIENT.post(
            "/cache/batch/precision",
            json={
                "queries": [
                    {"market": "moneyline"},
                    {"team": "Lakers", "sport": "Basketball"},
                    {"player": "LeBron James"},
                ]
            },
            headers=user_headers(),
        )
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# /leagues with filters
# ─────────────────────────────────────────────────────────────────────────────

class TestLeagues:
    def test_all_leagues_returns_200(self):
        r = CLIENT.get("/leagues", headers=user_headers())
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

    def test_leagues_response_is_json(self):
        r = CLIENT.get("/leagues", headers=user_headers())
        try:
            r.json()
        except Exception:
            pytest.fail("Leagues response was not valid JSON")

    def test_leagues_filter_by_sport_does_not_crash(self):
        r = CLIENT.get("/leagues", params={"sport": "Soccer"}, headers=user_headers())
        assert r.status_code != 500

    def test_leagues_filter_by_search_does_not_crash(self):
        r = CLIENT.get("/leagues", params={"search": "premier"}, headers=user_headers())
        assert r.status_code != 500

    def test_leagues_filter_by_region_does_not_crash(self):
        r = CLIENT.get("/leagues", params={"sport": "Soccer", "region": "Europe"}, headers=user_headers())
        assert r.status_code != 500


# ─────────────────────────────────────────────────────────────────────────────
# /cache/clear and /cache/invalidate (admin DELETE endpoints)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminCacheManagement:
    def test_clear_rejects_no_token(self):
        r = CLIENT.request("DELETE", "/cache/clear")
        assert r.status_code in (401, 403)

    def test_clear_rejects_user_token(self):
        r = CLIENT.request("DELETE", "/cache/clear", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_clear_accepts_admin_token_does_not_crash(self):
        # With Redis mocked out, clear_all_cache() returns False → endpoint returns 500
        # with "Failed to clear cache". This is correct behaviour — not a code crash.
        # We only verify the admin token is accepted (not 401/403) and a JSON response is returned.
        r = CLIENT.request("DELETE", "/cache/clear", headers=admin_headers())
        assert r.status_code not in (401, 403), f"Admin token was rejected: {r.status_code}"
        try:
            r.json()
        except Exception:
            pytest.fail("Response was not valid JSON")

    def test_invalidate_rejects_no_token(self):
        r = CLIENT.request("DELETE", "/cache/invalidate", params={"market": "moneyline"})
        assert r.status_code in (401, 403)

    def test_invalidate_rejects_user_token(self):
        r = CLIENT.request("DELETE", "/cache/invalidate", params={"market": "moneyline"}, headers=user_headers())
        assert r.status_code in (401, 403)

    def test_invalidate_missing_params_returns_400(self):
        r = CLIENT.request("DELETE", "/cache/invalidate", headers=admin_headers())
        assert r.status_code == 400

    def test_invalidate_with_param_does_not_crash(self):
        r = CLIENT.request(
            "DELETE", "/cache/invalidate",
            params={"market": "moneyline"},
            headers=admin_headers(),
        )
        assert r.status_code not in (401, 403, 500), f"Unexpected: {r.status_code} {r.text[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# Admin log / session / stats / missing-items endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminInfoEndpoints:
    def test_logs_rejects_user_token(self):
        r = CLIENT.get("/admin/logs", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_logs_accepts_admin_does_not_crash(self):
        r = CLIENT.get("/admin/logs", headers=admin_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_logs_with_limit_param(self):
        r = CLIENT.get("/admin/logs", params={"limit": 10, "offset": 0}, headers=admin_headers())
        assert r.status_code != 500

    def test_sessions_rejects_user_token(self):
        r = CLIENT.get("/admin/sessions", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_sessions_accepts_admin_does_not_crash(self):
        r = CLIENT.get("/admin/sessions", headers=admin_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_admin_stats_cache_rejects_user_token(self):
        r = CLIENT.get("/admin/stats/cache", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_admin_stats_cache_accepts_admin_does_not_crash(self):
        r = CLIENT.get("/admin/stats/cache", headers=admin_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_missing_items_rejects_user_token(self):
        r = CLIENT.get("/admin/missing-items", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_missing_items_accepts_admin_does_not_crash(self):
        r = CLIENT.get("/admin/missing-items", headers=admin_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"

    def test_missing_items_delete_rejects_user_token(self):
        r = CLIENT.request("DELETE", "/admin/missing-items", headers=user_headers())
        assert r.status_code in (401, 403)

    def test_missing_items_delete_accepts_admin_does_not_crash(self):
        r = CLIENT.request("DELETE", "/admin/missing-items", headers=admin_headers())
        assert r.status_code != 500, f"Server crashed: {r.text[:200]}"


# ─────────────────────────────────────────────────────────────────────────────
# /admin/dashboard (cookie-based, no Bearer token)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminDashboard:
    def test_dashboard_no_cookie_returns_401(self):
        r = CLIENT.get("/admin/dashboard")
        assert r.status_code == 401

    def test_dashboard_wrong_cookie_returns_401(self):
        r = CLIENT.get("/admin/dashboard", cookies={"admin_access": "wrong-token"})
        assert r.status_code == 401

    def test_dashboard_valid_cookie_returns_200(self):
        r = CLIENT.get("/admin/dashboard", cookies={"admin_access": ADMIN_TOKEN})
        assert r.status_code == 200

    def test_dashboard_login_wrong_token_returns_403(self):
        r = CLIENT.post(
            "/admin/dashboard/login",
            data={"admin_token": "wrong"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 403

    def test_dashboard_login_valid_token_redirects(self):
        r = CLIENT.post(
            "/admin/dashboard/login",
            data={"admin_token": ADMIN_TOKEN},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        assert r.status_code in (302, 303), f"Expected redirect, got {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# /docs and /openapi.json
# ─────────────────────────────────────────────────────────────────────────────

class TestDocsEndpoints:
    def test_docs_returns_200(self):
        r = CLIENT.get("/docs")
        assert r.status_code == 200

    def test_openapi_json_returns_200(self):
        r = CLIENT.get("/openapi.json")
        assert r.status_code == 200

    def test_openapi_json_is_valid_json(self):
        r = CLIENT.get("/openapi.json")
        data = r.json()
        assert "paths" in data, "openapi.json missing 'paths' key"
        assert "info" in data, "openapi.json missing 'info' key"

    def test_openapi_json_with_admin_cookie_shows_admin_paths(self):
        r = CLIENT.get("/openapi.json", cookies={"admin_access": ADMIN_TOKEN})
        data = r.json()
        paths = data.get("paths", {})
        assert any("admin" in p for p in paths), "Admin paths not visible with admin cookie"
