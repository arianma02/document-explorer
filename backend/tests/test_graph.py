from app.database import get_connection


def upload(client, content, filename):
    return client.post("/documents", files={"file": (filename, content, "text/plain")})


def test_empty_graph(client):
    response = client.get("/graph")
    assert response.status_code == 200
    assert response.json() == {"nodes": [], "edges": []}


def test_graph_connects_related_documents_with_source_evidence(client):
    solar = upload(
        client, b"Solar panels generate electricity from sunlight.", "solar.txt"
    ).json()
    energy = upload(
        client, b"Sunlight can be converted into electrical power.", "energy.txt"
    ).json()
    cat = upload(client, b"My cat sleeps on the sofa.", "cat.txt").json()
    response = client.get("/graph")
    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert {edge["source"], edge["target"]} == {solar["id"], energy["id"]}
    assert cat["id"] not in {edge["source"], edge["target"]}
    assert edge["score"] > 0.5
    for side in ("source", "target"):
        evidence = edge[side + "_passage"]
        assert evidence["document_id"] == edge[side]
        assert evidence["page_number"] is None
        assert "embedding" not in evidence
        stored = client.get(f"/documents/{edge[side]}/passages").json()
        assert evidence in stored


def test_graph_does_not_mix_embedding_models(client):
    upload(client, b"Solar panels generate electricity.", "first.txt")
    second = upload(client, b"Solar panels generate electricity.", "second.txt").json()
    with get_connection() as connection:
        connection.execute(
            "UPDATE passages SET embedding_model = %s WHERE document_id = %s",
            ("different-model", second["id"]),
        )
    graph = client.get("/graph?min_similarity=0").json()
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == []


def test_graph_limit_selects_newest_documents(client):
    upload(client, b"First document", "first.txt")
    newest = upload(client, b"Second document", "second.txt").json()
    graph = client.get("/graph?limit=1").json()
    assert [node["id"] for node in graph["nodes"]] == [newest["id"]]
    assert graph["edges"] == []


def test_graph_validates_filter_values(client):
    for query in ("limit=0", "limit=21", "min_similarity=-0.1", "min_similarity=1.1"):
        assert client.get("/graph?" + query).status_code == 422
