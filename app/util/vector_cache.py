import pickle

import numpy as np

from app.database import DocumentEmbedding

def deserialize_embedding(serialized_embedding):
    return pickle.loads(serialized_embedding)

class VectorCache:
    _instance = None
    _vectors = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorCache, cls).__new__(cls)
        return cls._instance

    @classmethod
    def clear_cache(cls):
        cls._vectors.clear()

    @classmethod
    def load_user_vectors(cls, user_id):
        cls.clear_cache()
        vector_data = {
            str(embedding.chunk_id): deserialize_embedding(embedding.embedding)
            for embedding in DocumentEmbedding.query.filter_by(user_id=user_id).all()
        }
        cls._vectors.update(vector_data)

    @classmethod
    def mips_naive(cls, query_vector, subset_ids):
        # Calculate inner product for each vector in the subset
        similarities = [
            (id, np.dot(query_vector, cls._vectors[id]))
            for id in subset_ids if id in cls._vectors
        ]

        # Sort by similarity in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities
