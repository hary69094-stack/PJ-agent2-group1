"""SentenceTransformer embedding encoder."""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize


class EmbeddingEncoder:
    """Wraps SentenceTransformer to produce L2-normalized embeddings."""

    def __init__(self, model_name: str = "shibing624/text2vec-base-chinese-sentence"):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into L2-normalized embedding vectors.

        Args:
            texts: List of text strings.

        Returns:
            numpy array of shape (len(texts), dim) with unit-norm rows.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,  # L2 normalization built-in
            show_progress_bar=False,
        )
        # Ensure float32 for FAISS compatibility
        return embeddings.astype(np.float32)
