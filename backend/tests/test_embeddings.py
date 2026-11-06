import math
from unittest.mock import patch

import pytest

from app.embeddings import EmbeddingModel, cosine_similarity


@pytest.fixture(scope="module")
def model():
    return EmbeddingModel()


def test_rejects_file_with_wrong_checksum_before_loading(tmp_path):
    path = tmp_path / "tampered.onnx"
    path.write_bytes(b"This is not the approved model.")
    with patch("app.embeddings.hf_hub_download", return_value=str(path)):
        with pytest.raises(ValueError, match="checksum mismatch"):
            EmbeddingModel()


def test_rejects_unapproved_file_without_downloading(model):
    with patch("app.embeddings.hf_hub_download") as download:
        with pytest.raises(ValueError, match="approved model files"):
            model.download("modeling.py")
        download.assert_not_called()


def test_returns_384_finite_normalized_numbers(model):
    vector = model.embed("Solar panels generate electricity.")
    assert len(vector) == 384
    assert all(math.isfinite(value) for value in vector)
    assert round(sum(value * value for value in vector) - 1, 5) == 0


def test_related_text_ranks_above_unrelated_text(model):
    first = model.embed("Solar panels generate electricity from sunlight.")
    related = model.embed("Sunlight can be converted into electrical power.")
    unrelated = model.embed("My cat sleeps on the sofa.")
    assert cosine_similarity(first, related) > cosine_similarity(first, unrelated)
    assert round(cosine_similarity(first, first) - 1, 5) == 0


def test_rejects_empty_and_overlong_input(model):
    with pytest.raises(ValueError, match="empty"):
        model.embed("  ")
    with pytest.raises(ValueError, match="256"):
        model.embed("energy " * 257)


def test_rejects_invalid_comparison_vectors():
    for first, second in [([], []), ([1], [1, 2]), ([0], [0]), ([float("nan")], [1])]:
        with pytest.raises(ValueError):
            cosine_similarity(first, second)
