import pickle
import numpy as np
from app.database import DocumentEmbedding

def deserialize_embedding(embedding_bytes):
    # Deserialize the numpy array from bytes using pickle
    try:
        embedding_array = pickle.loads(embedding_bytes)
    except Exception as e:
        raise ValueError("Failed to deserialize embedding: {}".format(e))

    # Check that the numpy array has the expected shape and dtype
    if embedding_array.dtype != np.float32:
        raise ValueError("Unexpected embedding array dtype: {}".format(embedding_array.dtype))
    if embedding_array.shape != (1536,):
        raise ValueError("Unexpected embedding array shape: {}".format(embedding_array.shape))

    return embedding_array


class VectorCache:
    _instance = None
    _vectors = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorCache, cls).__new__(cls)
        return cls._instance

    @classmethod
    def clear_cache(cls):
        print("Clearing the vector cache.")
        cls._vectors.clear()

    @classmethod
    def load_user_vectors(cls, user_id):
        cls.clear_cache()
        embeddings = DocumentEmbedding.query.filter_by(user_id=user_id).all()
        vector_data = {}

        for embedding in embeddings:
            vector = np.frombuffer(embedding.embedding, dtype=np.float32)
            vector_data[str(embedding.chunk_id)] = vector

        # Update the cache with new vectors
        cls._vectors.update(vector_data)

    @classmethod
    def mips_naive(cls, query_vector, subset_ids):
        # Ensure query_vector is a numpy array
        if not isinstance(query_vector, np.ndarray):
            raise ValueError("Query vector must be a numpy array.")

        # Ensure query_vector is 1D
        if query_vector.ndim != 1:
            raise ValueError("Query vector must be a 1D array.")

        # Debug: Print the number of vectors loaded
        print(f"Number of vectors loaded: {len(cls._vectors)}")
        print(f"Query vector dimensions: {query_vector.shape}")

        # Debug: Print the shapes of all loaded vectors
        for vector_id, vector in cls._vectors.items():
            print(f"Vector ID: {vector_id}, Shape: {vector.shape}")
        # Calculate inner product for each vector in the subset
        similarities = []
        for id in subset_ids:
            if id in cls._vectors:
                similarity = np.dot(query_vector, cls._vectors[id])
                similarities.append((id, similarity))
            else:
                # Debug: Print a message if an ID is not found in the cache
                print(f"ID {id} not found in the cache.")

        # Sort by similarity in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Debug: Print the similarities
        print(f"Similarities: {similarities}")

        return similarities
