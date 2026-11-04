import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.embeddings import EmbeddingModel, cosine_similarity


def setUpModule():
    global model
    model = EmbeddingModel()


class EmbeddingTests(unittest.TestCase):
    def test_rejects_file_with_wrong_checksum_before_loading(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.onnx"
            path.write_bytes(b"This is not the approved model.")
            with patch("app.embeddings.hf_hub_download", return_value=str(path)):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    EmbeddingModel()

    def test_rejects_unapproved_file_without_downloading(self):
        with patch("app.embeddings.hf_hub_download") as download:
            with self.assertRaisesRegex(ValueError, "approved model files"):
                model.download("modeling.py")
            download.assert_not_called()

    def test_returns_384_finite_normalized_numbers(self):
        vector = model.embed("Solar panels generate electricity.")
        self.assertEqual(len(vector), 384)
        self.assertTrue(all(math.isfinite(value) for value in vector))
        self.assertAlmostEqual(sum(value * value for value in vector), 1, places=5)

    def test_related_text_ranks_above_unrelated_text(self):
        first = model.embed("Solar panels generate electricity from sunlight.")
        related = model.embed("Sunlight can be converted into electrical power.")
        unrelated = model.embed("My cat sleeps on the sofa.")
        self.assertGreater(
            cosine_similarity(first, related), cosine_similarity(first, unrelated)
        )
        self.assertAlmostEqual(cosine_similarity(first, first), 1, places=5)

    def test_rejects_empty_and_overlong_input(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            model.embed("  ")
        with self.assertRaisesRegex(ValueError, "256"):
            model.embed("energy " * 257)

    def test_rejects_invalid_comparison_vectors(self):
        for first, second in [
            ([], []),
            ([1], [1, 2]),
            ([0], [0]),
            ([float("nan")], [1]),
        ]:
            with self.subTest(first=first, second=second):
                with self.assertRaises(ValueError):
                    cosine_similarity(first, second)
