"""Embeddings multilíngues leves para BERTScore e similaridade semântica.

Modelo: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (Apache-2.0),
versão ONNX quantizada para AVX2 (~112 MB), baixada do Hugging Face no primeiro uso e
executada com onnxruntime (já instalado). Roda bem em CPU sem GPU.
"""

from __future__ import annotations

import threading

import numpy as np

REPO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_FILE = "onnx/model_quint8_avx2.onnx"
MAX_TOKENS = 256


class Encoder:
    def __init__(self, model_path: str, tokenizer_path: str) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2  # deixa CPU para o resto do PC
        self.session = ort.InferenceSession(model_path, options, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.tokenizer.enable_truncation(MAX_TOKENS)

    def _run(self, text: str) -> tuple[np.ndarray, np.ndarray]:
        encoding = self.tokenizer.encode(text)
        ids = np.array([encoding.ids], dtype=np.int64)
        mask = np.array([encoding.attention_mask], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self.inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        hidden = self.session.run(None, feed)[0][0]  # (tokens, 384)
        return hidden, np.array(encoding.special_tokens_mask, dtype=bool)

    def token_embeddings(self, text: str) -> np.ndarray:
        """Vetores normalizados dos tokens (sem [CLS]/[SEP]), como no BERTScore."""
        if not text.strip():
            return np.zeros((0, 384), dtype=np.float32)
        hidden, special = self._run(text)
        vectors = hidden[~special]
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-9)

    def sentence_embedding(self, text: str) -> np.ndarray:
        """Média dos tokens (mean pooling, como o sentence-transformers), normalizada."""
        hidden, special = self._run(text)
        vector = hidden[~special].mean(axis=0) if (~special).any() else hidden.mean(axis=0)
        return vector / max(float(np.linalg.norm(vector)), 1e-9)

    def similarity(self, a: str, b: str) -> float:
        if not a.strip() or not b.strip():
            return 0.0
        return float(self.sentence_embedding(a) @ self.sentence_embedding(b))


_encoder: Encoder | None = None
_lock = threading.Lock()


def default_encoder() -> Encoder:
    global _encoder
    with _lock:
        if _encoder is None:
            from huggingface_hub import hf_hub_download

            model = hf_hub_download(REPO, MODEL_FILE)
            tokenizer = hf_hub_download(REPO, "tokenizer.json")
            _encoder = Encoder(model, tokenizer)
    return _encoder


def available() -> bool:
    """O modelo já está baixado? (para não travar uma resposta baixando 112 MB)"""
    try:
        from huggingface_hub import try_to_load_from_cache

        return isinstance(try_to_load_from_cache(REPO, MODEL_FILE), str)
    except Exception:
        return False
