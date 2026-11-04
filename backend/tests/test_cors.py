import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.origin = "https://arianma02.github.io"

    def test_frontend_can_read_responses_including_errors(self):
        for path, status in [("/health", 200), ("/missing-page", 404)]:
            with self.subTest(path=path):
                response = self.client.get(path, headers={"Origin": self.origin})
                self.assertEqual(response.status_code, status)
                self.assertEqual(
                    response.headers["access-control-allow-origin"], self.origin
                )

    def test_frontend_can_preflight_uploads_and_deletions(self):
        for method in ["POST", "DELETE"]:
            with self.subTest(method=method):
                response = self.client.options(
                    "/documents/1",
                    headers={
                        "Origin": self.origin,
                        "Access-Control-Request-Method": method,
                        "Access-Control-Request-Headers": "content-type",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"], self.origin
                )

    def test_other_origins_do_not_receive_cors_permission(self):
        response = self.client.options(
            "/documents/1",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)
