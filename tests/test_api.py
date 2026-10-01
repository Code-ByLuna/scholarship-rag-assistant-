import pytest
from core.corpus import records
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_profile_initial_fields_only(client):
    p = {
        "state": "Kerala",
        "category": "OBC",
        "annual_family_income": 250000,
        "course_level": "undergraduate",
        "year_of_study": 3,
        "study_mode": "regular",
    }
    r = client.post("/api/profile/validate", p, format="json")
    assert r.status_code == 200
    assert r.json()["profile"]["gender"] is None
    assert client.post("/api/profile/validate", {}, format="json").status_code == 400


def test_eligibility_search_detail(client):
    result = client.post("/api/eligibility/check", {"profile": {}}, format="json")
    assert result.status_code == 200
    assert len(result.json()["results"]) == 16
    search = client.post("/api/scholarships/search", {"category": "OBC"}, format="json")
    assert any("yasasvi" in s["scheme_id"] for s in search.json()["results"])
    sid = records()[0]["scheme_id"]
    assert client.get("/api/scholarships/" + sid).status_code == 200
    assert client.get("/api/scholarships/unknown").status_code == 404


def test_session_token_required(client):
    result = client.post("/api/sessions", {}, format="json")
    assert result.status_code == 201
    session = result.json()
    path = "/api/sessions/" + session["session_id"]
    assert client.get(path).status_code == 404
    assert client.get(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 200


def test_admin_endpoints_protected(client):
    assert client.post("/api/admin/ingest", {}, format="json").status_code in (401, 403)
    assert client.get("/api/agent/usage").status_code in (401, 403)


def test_request_id_and_invalid_input(client):
    response = client.post(
        "/api/eligibility/check",
        {"profile": {"age": "unknown"}},
        format="json",
        HTTP_X_REQUEST_ID="test-request",
    )
    assert response.status_code == 400
    assert response["X-Request-ID"] == "test-request"
    assert "unknown" not in str(response.json()["error"])


def test_invalid_session_and_delete(client):
    assert client.get("/api/sessions/not-a-uuid").status_code == 404
    session = client.post("/api/sessions", {}, format="json").json()
    path = "/api/sessions/" + session["session_id"]
    assert client.delete(path).status_code == 404
    assert client.delete(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 204
    assert client.get(path, HTTP_X_SESSION_TOKEN=session["session_token"]).status_code == 404


def test_health_exposes_real_index_status(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["dataset"]["records"] == 16
    assert isinstance(response.json()["vector_index"]["ready"], bool)
