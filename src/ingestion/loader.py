from typing import List, Dict, Any
import hashlib

class DocumentLoader:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def load_document(self, file_path: str) -> Dict[str, Any]:
        """
        Loads a document and extracts text.
        """
        # Mock loader
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_hash = hashlib.sha256(content.encode()).hexdigest()
        
        return {
            "content": content,
            "hash": doc_hash,
            "metadata": {
                "source": file_path
            }
        }

    def chunk_document(self, document: Dict[str, Any], chunk_size: int = 500) -> List[Dict[str, Any]]:
        """
        Splits document into chunks.
        """
        text = document['content']
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        return [
            {
                "text": chunk,
                "metadata": document['metadata']
            }
            for chunk in chunks
        ]
