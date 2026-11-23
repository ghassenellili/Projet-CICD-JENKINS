"""HTTP integration tests for the Flask Error Budget Calculator endpoints."""

import pytest

from app.main import create_app


@pytest.fixture()
def client():
    """Configure a Flask test client for HTTP integration tests."""
    app = create_app()
    app.config.update({"TESTING": True})
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint_returns_ok(client):
    """GET /health must return HTTP 200 and body 'OK'."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.data.decode("utf-8").strip() == "OK"


def test_get_downtime_endpoint(client):
    """GET /slo/downtime?slo=99.9&days=30 returns exact downtime JSON."""
    response = client.get("/slo/downtime?slo=99.9&days=30")
    assert response.status_code == 200
    data = response.get_json()
    assert data["slo_target"] == 99.9
    assert data["window_days"] == 30
    assert data["allowed_downtime_minutes"] == 43.2


def test_post_budget_endpoint(client):
    """POST /slo/budget computes remaining error budget over HTTP."""
    payload = {
        "slo_target": 99.9,
        "total_requests": 100000,
        "failed_requests": 40,
    }
    response = client.post("/slo/budget", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["allowed_failures"] == 100
    assert data["remaining_failures"] == 60
    assert data["budget_exhausted"] is False


def test_post_release_check_go_and_nogo(client):
    """POST /slo/release-check returns GO when healthy and NO-GO when exhausted."""
    go_resp = client.post(
        "/slo/release-check",
        json={"slo_target": 99.9, "total_requests": 100000, "failed_requests": 10},
    )
    assert go_resp.status_code == 200
    assert go_resp.get_json()["decision"] == "GO"

    nogo_resp = client.post(
        "/slo/release-check",
        json={"slo_target": 99.9, "total_requests": 100000, "failed_requests": 200},
    )
    assert nogo_resp.status_code == 200
    assert nogo_resp.get_json()["decision"] == "NO-GO"


def test_post_release_check_blocks_when_budget_exceeded(client):
    """POST /slo/release-check returns NO-GO when failures exceed the error budget."""
    payload = {
        "slo_target": 99.9,
        "total_requests": 100000,
        "failed_requests": 150,
    }
    response = client.post("/slo/release-check", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["decision"] == "NO-GO"
    assert data["can_deploy"] is False


def test_invalid_http_request_returns_400(client):
    """Invalid SLO payload over HTTP returns HTTP 400 Bad Request."""
    response = client.post(
        "/slo/budget",
        json={"slo_target": 105.0, "total_requests": 1000, "failed_requests": 0},
    )
    assert response.status_code == 400
    assert "error" in response.get_json()
