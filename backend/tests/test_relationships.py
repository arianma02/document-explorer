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


def test_empty_collection_and_documents_without_embeddings():
    assert build_graph([], [], 0.5) == {"nodes": [], "edges": []}
    documents = [{"id": 1}, {"id": 2}]
    assert build_graph(documents, [], 0.5) == {"nodes": documents, "edges": []}


def test_selects_strongest_pair_and_preserves_evidence():
    documents = [{"id": 1}, {"id": 2}]
    passages = [
        passage(1, 1, [1, 0]),
        passage(2, 1, [0, 1]),
        passage(3, 2, [0.8, 0.6], page=4),
    ]
    edges = build_graph(documents, passages, 0.5)["edges"]
    assert len(edges) == 1
    edge = edges[0]
    assert round(edge["score"] - 0.8, 7) == 0
    assert edge["source_passage"]["id"] == 1
    assert edge["target_passage"]["id"] == 3
    assert edge["target_passage"]["page_number"] == 4
    assert "embedding" not in edge["source_passage"]


def test_threshold_filters_connections():
    documents = [{"id": 1}, {"id": 2}]
    passages = [passage(1, 1, [1, 0]), passage(2, 2, [0.8, 0.6])]
    assert len(build_graph(documents, passages, 0.8)["edges"]) == 1
    assert build_graph(documents, passages, 0.81)["edges"] == []


def test_no_self_edges_or_duplicate_pairs_and_scores_sorted():
    documents = [{"id": 1}, {"id": 2}, {"id": 3}]
    passages = [passage(1, 1, [1, 0]), passage(2, 2, [0.8, 0.6]), passage(3, 3, [0, 1])]
    edges = build_graph(documents, passages, 0)["edges"]
    assert len(edges) == 3
    assert all(edge["source"] != edge["target"] for edge in edges)
    assert [edge["score"] for edge in edges] == [0.8, 0.6, 0]
