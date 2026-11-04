import unittest

from app.relationships import build_graph


def passage(passage_id, document_id, embedding, page=1):
    return {
        "id": passage_id,
        "document_id": document_id,
        "position": passage_id,
        "page_number": page,
        "text": f"Source text {passage_id}",
        "embedding": embedding,
    }


class RelationshipTests(unittest.TestCase):
    def test_empty_collection_and_documents_without_embeddings(self):
        self.assertEqual(build_graph([], [], 0.5), {"nodes": [], "edges": []})
        documents = [{"id": 1}, {"id": 2}]
        self.assertEqual(
            build_graph(documents, [], 0.5), {"nodes": documents, "edges": []}
        )

    def test_selects_strongest_pair_and_preserves_evidence(self):
        documents = [{"id": 1}, {"id": 2}]
        passages = [
            passage(1, 1, [1, 0]),
            passage(2, 1, [0, 1]),
            passage(3, 2, [0.8, 0.6], page=4),
        ]
        edges = build_graph(documents, passages, 0.5)["edges"]
        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertAlmostEqual(edge["score"], 0.8)
        self.assertEqual(edge["source_passage"]["id"], 1)
        self.assertEqual(edge["target_passage"]["id"], 3)
        self.assertEqual(edge["target_passage"]["page_number"], 4)
        self.assertNotIn("embedding", edge["source_passage"])

    def test_threshold_filters_connections(self):
        documents = [{"id": 1}, {"id": 2}]
        passages = [passage(1, 1, [1, 0]), passage(2, 2, [0.8, 0.6])]
        self.assertEqual(len(build_graph(documents, passages, 0.8)["edges"]), 1)
        self.assertEqual(build_graph(documents, passages, 0.81)["edges"], [])

    def test_no_self_edges_or_duplicate_pairs_and_scores_sorted(self):
        documents = [{"id": 1}, {"id": 2}, {"id": 3}]
        passages = [
            passage(1, 1, [1, 0]),
            passage(2, 2, [0.8, 0.6]),
            passage(3, 3, [0, 1]),
        ]
        edges = build_graph(documents, passages, 0)["edges"]
        self.assertEqual(len(edges), 3)
        self.assertTrue(all(edge["source"] != edge["target"] for edge in edges))
        self.assertEqual([edge["score"] for edge in edges], [0.8, 0.6, 0])
