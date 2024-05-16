import pickle
import threading

import numpy as np
from sqlalchemy.orm import load_only

from app.models.embedding_models import Document, DocumentChunk, DocumentEmbedding
class VectorCache:
    _instance = None
    _vectors = np.array([])  # Store vectors as a single numpy array
    _ids = []  # Store corresponding chunk IDs
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorCache, cls).__new__(cls)
        return cls._instance

    @classmethod
    def clear_cache(cls) -> None:
        with cls._lock:
            cls._vectors = np.array([])
            cls._ids = []

    @classmethod
    def load_user_vectors(cls, user_id: int) -> None:
        cls.clear_cache()
        embeddings = (
            DocumentEmbedding.query
            .join(DocumentChunk, DocumentChunk.id == DocumentEmbedding.chunk_id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(DocumentEmbedding.user_id == user_id, Document.delete == False)
            .options(load_only(DocumentEmbedding.chunk_id, DocumentEmbedding.embedding))
            .all()
        )

        if not embeddings:
            return

        with cls._lock:
            cls._vectors = np.stack([np.frombuffer(embedding.embedding, dtype=np.float32) for embedding in embeddings])
            cls._ids = [str(embedding.chunk_id) for embedding in embeddings]
    @classmethod
    def mips_naive(cls, query_vector: np.ndarray, subset_ids: list) -> list:
        if not isinstance(query_vector, np.ndarray):
            raise ValueError("Query vector must be a numpy array.")
        if query_vector.ndim != 1:
            raise ValueError("Query vector must be a 1D array.")

        with cls._lock:
            subset_indices = [cls._ids.index(str(chunk_id)) for chunk_id in subset_ids if str(chunk_id) in cls._ids]
            subset_vectors = cls._vectors[subset_indices]

        # Calculate dot products using NumPy's vectorized operations
        similarities = np.dot(subset_vectors, query_vector)

        # Combine IDs and similarities, then sort by similarity score in descending order
        ranked_similarities = sorted(zip([cls._ids[i] for i in subset_indices], similarities), key=lambda x: x[1], reverse=True)

        return [(chunk_id, rank + 1) for rank, (chunk_id, _) in enumerate(ranked_similarities)]