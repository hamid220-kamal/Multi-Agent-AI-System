import chromadb
import uuid
import os
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

# Use a local directory for persistent RAG memory
DB_PATH = os.path.join(os.path.dirname(__file__), "..", ".chroma_db")
os.makedirs(DB_PATH, exist_ok=True)

class OfflineDummyEmbedding(EmbeddingFunction):
    """
    A lightweight, fully offline dummy embedding function that doesn't 
    try to download external ONNX models (to bypass network/DNS blocks).
    It generates deterministic pseudo-random embeddings.
    """
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            # Create a simple deterministic 384-dimensional vector from the string hash
            # This ensures ChromaDB can operate 100% locally and offline without downloading models
            base_val = float(abs(hash(text)) % 1000) / 1000.0
            vec = [base_val] * 384
            embeddings.append(vec)
        return embeddings

class LocalVectorMemory:
    """
    A lightweight Vector Database wrapper using ChromaDB.
    It stores and retrieves agent memories locally without needing a cloud service.
    """
    def __init__(self, collection_name: str = "agent_memory_offline"):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=OfflineDummyEmbedding()
        )

    def add_memory(self, text: str, metadata: dict = None):
        """Stores a piece of text into the vector database."""
        if not text or not str(text).strip():
            return None
            
        doc_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
        return doc_id

    def query_memory(self, query: str, n_results: int = 3):
        """Retrieves semantically similar memories based on the query."""
        if self.collection.count() == 0:
            return []
            
        # Ensure we don't ask for more results than we have in the DB
        safe_n_results = min(n_results, self.collection.count())
        if safe_n_results == 0:
            return []
            
        results = self.collection.query(
            query_texts=[query],
            n_results=safe_n_results
        )
        
        # Chroma returns a list of lists for documents, we just want the first sub-list
        return results.get("documents", [[]])[0]

# Global memory instance
vector_memory = LocalVectorMemory()
