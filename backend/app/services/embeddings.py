"""Local multilingual sentence embeddings, with no hosted embedding API."""

from collections.abc import Sequence
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MODEL_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "sentence-transformers"


class EmbeddingError(RuntimeError):
    """A diagnostic suitable for the operator command."""


def _load_sentence_transformer(cache_dir: Path, local_files_only: bool):
    # Keep the large, optional ML runtime out of API startup and ordinary tests.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL_NAME,
        revision=MODEL_REVISION,
        device="cpu",
        cache_folder=str(cache_dir),
        local_files_only=local_files_only,
        trust_remote_code=False,
        token=False,
        model_kwargs={"use_safetensors": True},
    )


class LocalEmbeddings:
    model = MODEL_NAME
    dimensions = 384
    batch_size = 32

    def __init__(
        self, *, cache_dir: Path = MODEL_CACHE, local_files_only: bool = False
    ):
        self._cache_dir = cache_dir
        self._local_files_only = local_files_only
        self._encoder = None

    @property
    def profile(self) -> dict:
        return {
            "provider": "sentence-transformers",
            "model": self.model,
            "revision": MODEL_REVISION,
            "dimensions": self.dimensions,
            "normalization": "l2",
            "pooling": "token-weighted-segments-v1",
        }

    def load(self) -> None:
        """Download/cache once, or load strictly offline when requested."""
        if self._encoder is not None:
            return
        try:
            encoder = _load_sentence_transformer(
                self._cache_dir, self._local_files_only
            )
        except ImportError:
            raise EmbeddingError(
                "Install local embedding dependencies: pip install -r requirements-rag.txt."
            ) from None
        except (OSError, RuntimeError, ValueError):
            raise EmbeddingError(
                "Local embedding model could not load; check the cache or download it without --offline."
            ) from None
        if encoder.get_sentence_embedding_dimension() != self.dimensions:
            raise EmbeddingError("Local model has an unexpected embedding dimension.")
        if encoder.max_seq_length <= encoder.tokenizer.num_special_tokens_to_add(False):
            raise EmbeddingError("Local model has an invalid token limit.")
        self._encoder = encoder

    def _segments(self, text: str) -> list[tuple[str, int]]:
        """Lossless subdivisions prevent SentenceTransformer's silent truncation."""
        tokenizer = self._encoder.tokenizer
        limit = self._encoder.max_seq_length - tokenizer.num_special_tokens_to_add(
            False
        )
        tokens = tokenizer.encode(
            text, add_special_tokens=False, truncation=False, verbose=False
        )
        if len(tokens) <= limit:
            return [(text, max(1, len(tokens)))]
        if len(text) < 2:
            raise EmbeddingError("A character exceeds the local model token limit.")
        midpoint = len(text) // 2
        # Prefer a nearby word boundary, preserving every source character.
        boundary = text.rfind(" ", max(1, midpoint // 2), midpoint + 1)
        split = boundary + 1 if boundary > 0 else midpoint
        return self._segments(text[:split]) + self._segments(text[split:])

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if (
            isinstance(texts, (str, bytes))
            or not isinstance(texts, Sequence)
            or not 1 <= len(texts) <= self.batch_size
        ):
            raise ValueError(f"Provide between 1 and {self.batch_size} texts.")
        for value in texts:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Embedding input must contain nonblank text.")
            if len(value) > 20_000 or "\x00" in value:
                raise ValueError(
                    "Embedding input exceeds 20000 characters or contains NUL."
                )
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError(
                    "Embedding input must contain valid Unicode."
                ) from None
        self.load()
        try:
            groups = [self._segments(value) for value in texts]
            segments = [segment for group in groups for segment, _ in group]
            vectors = np.asarray(
                self._encoder.encode(
                    segments,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
            )
            if (
                vectors.shape != (len(segments), self.dimensions)
                or vectors.dtype.kind != "f"
                or not np.isfinite(vectors).all()
                or np.any(np.linalg.norm(vectors.astype(np.float64), axis=1) < 1e-12)
            ):
                raise EmbeddingError("Local model returned invalid vectors.")
            result = []
            offset = 0
            for group in groups:
                weights = [weight for _, weight in group]
                pooled = np.average(
                    vectors[offset : offset + len(group)].astype(np.float64),
                    axis=0,
                    weights=weights,
                )
                norm = np.linalg.norm(pooled)
                if not np.isfinite(norm) or norm < 1e-12:
                    raise EmbeddingError(
                        "Local model returned an invalid pooled vector."
                    )
                result.append((pooled / norm).astype(np.float32).tolist())
                offset += len(group)
            return result
        except EmbeddingError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError):
            raise EmbeddingError("Local embedding generation failed.") from None
