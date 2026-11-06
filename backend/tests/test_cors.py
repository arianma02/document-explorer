import pytest
from fastapi.testclient import TestClient

from app.main import app

origin = "https://arianma02.github.io"


@pytest.fixture
def client():
    return TestClient(app)


def test_frontend_can_read_responses_including_errors(client):
    for path, status in [("/health", 200), ("/missing-page", 404)]:
        response = client.get(path, headers={"Origin": origin})
        assert response.status_code == status
        assert response.headers["access-control-allow-origin"] == origin


def test_frontend_can_preflight_uploads_and_deletions(client):
    for method in ["POST", "DELETE"]:
        response = client.options(
            "/documents/1",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_other_origins_do_not_receive_cors_permission(client):
    response = client.options(
        "/documents/1",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
