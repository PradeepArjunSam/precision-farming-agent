
from src.tools.scraper import ScraperTool
import os
# Disable TensorFlow to avoid Keras 3 compatibility issues
os.environ['USE_TF'] = '0'
os.environ['USE_TORCH'] = '1'

import chromadb
from sentence_transformers import SentenceTransformer
import uuid

def populate():
    print("Populating ChromaDB with test data...")
    
    # We'll mock the scraper for now to ensure we have exact data for the tests
    # In a real scenario, we'd use scraper.run()
    
    data = [
        # Wheat Data
        {
            "text": "Wheat irrigation during tillering: Apply 30mm of water per week. Critical to maintain soil moisture at 70%. Source: fao.org/wheat",
            "metadata": {"source": "fao.org/wheat", "topic": "irrigation", "crop": "wheat"}
        },
        {
            "text": "Wheat tillering stage requires Nitrogen application. Apply 40kg/ha N. Source: usda.gov/wheat-guide",
            "metadata": {"source": "usda.gov/wheat-guide", "topic": "fertilizer", "crop": "wheat"}
        },
        
        # Corn Data
        {
            "text": "Corn fertilization: Vegetative stage (V6) requires high Nitrogen. Apply 150 lbs/acre of N. Phosphorus and Potassium should be applied pre-plant. Source: extension.crops.org/corn",
            "metadata": {"source": "extension.crops.org/corn", "topic": "fertilizer", "crop": "corn"}
        },
        {
             "text": "Corn Nitrogen deficiency symptoms: Yellowing in V-shape starting at leaf tip. Source: fao.org/corn-diseases",
             "metadata": {"source": "fao.org/corn-diseases", "topic": "deficiency", "crop": "corn"}
        }
    ]
    
    from chromadb.utils import embedding_functions
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    client = chromadb.PersistentClient(path="data/chroma")
    col = client.get_or_create_collection(
        name="agronomy_knowledge",
        embedding_function=embedding_fn
    )
    
    # Add to DB
    ids = [str(uuid.uuid4()) for _ in data]
    texts = [d["text"] for d in data]
    metadatas = [d["metadata"] for d in data]
    
    col.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )
    
    print(f"Added {len(data)} documents.")
    print("Current DB count:", col.count())

if __name__ == "__main__":
    populate()
