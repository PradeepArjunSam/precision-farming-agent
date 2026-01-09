from typing import Dict, Any, List, Optional
import chromadb
from chromadb.utils import embedding_functions
from .base import BaseTool
import uuid

class RetrieverTool(BaseTool):
    def __init__(self, db_path: str, collection_name: str = "agronomy_knowledge"):
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize Client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Initialize Embedding Function (using default SentenceTransformer)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or Create Collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )

    @property
    def name(self) -> str:
        return "retriever_tool"

    @property
    def description(self) -> str:
        return "Retrieves verified agronomy documents based on semantic query."

    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Ingests documents into the vector store.
        Expecting list of dicts: {'text': str, 'metadata': dict}
        """
        if not documents:
            return

        ids = [str(uuid.uuid4()) for _ in documents]
        texts = [doc['text'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]

        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

    def run(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """
        Performs semantic search.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

        # ChromaDB returns lists of lists (one for each query)
        if not results['documents']:
             return {"documents": []}

        # Flatten results
        retrieved_docs = []
        for i in range(len(results['documents'][0])):
            retrieved_docs.append({
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                "distance": results['distances'][0][i] if results['distances'] else None
            })

        return {
            "query": query,
            "documents": retrieved_docs
        }
