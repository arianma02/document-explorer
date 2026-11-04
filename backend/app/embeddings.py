import hashlib
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_ID = MODEL_NAME + "@" + MODEL_REVISION + "/onnx/model_quint8_avx2.onnx"
MODEL_CACHE = Path(__file__).resolve().parents[1] / ".models"
MAX_TOKENS = 256
MODEL_FILES = {
    "onnx/model_quint8_avx2.onnx": "b941bf19f1f1283680f449fa6a7336bb5600bdcd5f84d10ddc5cd72218a0fd21",
    "tokenizer.json": "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037",
}


class EmbeddingModel:
    """Load the pinned English model once and reuse it across passages.

    The first load downloads public model files. Later loads use the local cache.
    """

    def __init__(self):
        model_path = self.download("onnx/model_quint8_avx2.onnx")
        tokenizer_path = self.download("tokenizer.json")
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        # Check the full input ourselves rather than silently dropping excess tokens.
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            model_path, sess_options=options, providers=["CPUExecutionProvider"]
        )

    def download(self, filename):
        if filename not in MODEL_FILES:
            raise ValueError("This file is not part of the approved model files.")
        path = hf_hub_download(
            repo_id=MODEL_NAME,
            filename=filename,
            revision=MODEL_REVISION,
            cache_dir=str(MODEL_CACHE),
            token=False,
        )
        # Check cached files too, before passing their contents to model parsers.
        with open(path, "rb") as file:
            checksum = hashlib.file_digest(file, "sha256").hexdigest()
        if checksum != MODEL_FILES[filename]:
            raise ValueError(f"Model file checksum mismatch: {filename}")
        return path

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text.")
        tokens = self.tokenizer.encode(text)
        if len(tokens.ids) > MAX_TOKENS:
            raise ValueError(
                "Text exceeds 256 model tokens. Split it into smaller passages."
            )

        inputs = {
            "input_ids": np.array([tokens.ids], dtype=np.int64),
            "attention_mask": np.array([tokens.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([tokens.type_ids], dtype=np.int64),
        }
        outputs = self.session.run(None, inputs)
        first_output = outputs[0]
        token_vectors = first_output[0]
        # Average each of the 384 columns across the input tokens.
        passage_vector = token_vectors.mean(axis=0)
        vector_length = np.linalg.norm(passage_vector)
        normalized_vector = passage_vector / vector_length
        return normalized_vector.tolist()


def cosine_similarity(first: list[float], second: list[float]) -> float:
    """Compare vector directions. A larger score indicates greater similarity."""
    if not first or len(first) != len(second):
        raise ValueError("Vectors must be nonempty and have matching dimensions.")
    first_vector = np.array(first)
    second_vector = np.array(second)
    if not np.isfinite(first_vector).all() or not np.isfinite(second_vector).all():
        raise ValueError("Vectors must contain finite numbers.")
    first_length = np.linalg.norm(first_vector)
    second_length = np.linalg.norm(second_vector)
    if first_length == 0 or second_length == 0:
        raise ValueError("Cannot compare zero-length vectors.")
    dot_product = np.dot(first_vector, second_vector)
    score = dot_product / (first_length * second_length)
    return float(np.clip(score, -1, 1))
