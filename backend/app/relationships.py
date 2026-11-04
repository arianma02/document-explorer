import numpy as np


def passage_details(passage):
    return {
        "id": passage["id"],
        "document_id": passage["document_id"],
        "position": passage["position"],
        "page_number": passage["page_number"],
        "text": passage["text"],
    }


def build_graph(documents: list[dict], passages: list[dict], min_similarity: float):
    """Score each document pair using its strongest passage match.

    Scores describe semantic similarity, not agreement or factual correctness.
    Passage embeddings must be normalized and produced by the same model.
    """
    grouped_passages = {}
    for document in documents:
        grouped_passages[document["id"]] = []
    for passage in passages:
        grouped_passages[passage["document_id"]].append(passage)

    edges = []
    for source_index, source in enumerate(documents):
        source_passages = grouped_passages[source["id"]]
        if not source_passages:
            continue
        source_vectors = np.array([item["embedding"] for item in source_passages])
        for target in documents[source_index + 1 :]:
            target_passages = grouped_passages[target["id"]]
            if not target_passages:
                continue
            target_vectors = np.array([item["embedding"] for item in target_passages])
            # Stored vectors have length 1, so their dot products are cosine scores.
            scores = np.matmul(source_vectors, target_vectors.T)
            source_match_index, target_match_index = np.unravel_index(
                np.argmax(scores), scores.shape
            )
            score = float(
                np.clip(scores[source_match_index, target_match_index], -1, 1)
            )
            if score < min_similarity:
                continue
            edges.append(
                {
                    "source": source["id"],
                    "target": target["id"],
                    "score": score,
                    "source_passage": passage_details(
                        source_passages[source_match_index]
                    ),
                    "target_passage": passage_details(
                        target_passages[target_match_index]
                    ),
                }
            )
    edges.sort(key=lambda edge: edge["score"], reverse=True)
    return {"nodes": documents, "edges": edges}
