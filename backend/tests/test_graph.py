import unittest

from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app
from tests.database_helpers import prepare_test_database


def setUpModule():
    prepare_test_database()


class GraphApiTests(unittest.TestCase):
    def setUp(self):
        with get_connection() as connection:
            connection.execute("DELETE FROM documents")
        self.client = self.enterContext(TestClient(app))

    def upload(self, content, filename):
        return self.client.post(
            "/documents", files={"file": (filename, content, "text/plain")}
        )

    def test_empty_graph(self):
        response = self.client.get("/graph")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"nodes": [], "edges": []})

    def test_graph_connects_related_documents_with_source_evidence(self):
        solar = self.upload(
            b"Solar panels generate electricity from sunlight.", "solar.txt"
        ).json()
        energy = self.upload(
            b"Sunlight can be converted into electrical power.", "energy.txt"
        ).json()
        cat = self.upload(b"My cat sleeps on the sofa.", "cat.txt").json()
        response = self.client.get("/graph")
        self.assertEqual(response.status_code, 200)
        graph = response.json()
        self.assertEqual(len(graph["nodes"]), 3)
        self.assertEqual(len(graph["edges"]), 1)
        edge = graph["edges"][0]
        self.assertEqual({edge["source"], edge["target"]}, {solar["id"], energy["id"]})
        self.assertNotIn(cat["id"], {edge["source"], edge["target"]})
        self.assertGreater(edge["score"], 0.5)
        for side in ("source", "target"):
            evidence = edge[side + "_passage"]
            self.assertEqual(evidence["document_id"], edge[side])
            self.assertIsNone(evidence["page_number"])
            self.assertNotIn("embedding", evidence)
            stored = self.client.get(f"/documents/{edge[side]}/passages").json()
            self.assertIn(evidence, stored)

    def test_graph_does_not_mix_embedding_models(self):
        self.upload(b"Solar panels generate electricity.", "first.txt")
        second = self.upload(b"Solar panels generate electricity.", "second.txt").json()
        with get_connection() as connection:
            connection.execute(
                "UPDATE passages SET embedding_model = %s WHERE document_id = %s",
                ("different-model", second["id"]),
            )
        graph = self.client.get("/graph?min_similarity=0").json()
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(graph["edges"], [])

    def test_graph_limit_selects_newest_documents(self):
        self.upload(b"First document", "first.txt")
        newest = self.upload(b"Second document", "second.txt").json()
        graph = self.client.get("/graph?limit=1").json()
        self.assertEqual([node["id"] for node in graph["nodes"]], [newest["id"]])
        self.assertEqual(graph["edges"], [])

    def test_graph_validates_filter_values(self):
        for query in (
            "limit=0",
            "limit=21",
            "min_similarity=-0.1",
            "min_similarity=1.1",
        ):
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/graph?" + query).status_code, 422)
