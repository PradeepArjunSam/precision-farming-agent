
import chromadb
import sys
import os

def check_db():
    print("Checking ChromaDB content...")
    db_path = "data/chroma"
    
    if not os.path.exists(db_path):
        print(f"❌ DB Path does not exist: {db_path}")
        return

    try:
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        print(f"Found {len(collections)} collections.")
        
        for col in collections:
            print(f"\nCollection: {col.name}")
            print(f"Count: {col.count()}")
            if col.count() > 0:
                peek = col.peek(limit=3)
                print("Examples:")
                for i, doc in enumerate(peek['documents']):
                    print(f"  {i+1}. {doc[:100]}...")
                    print(f"     Meta: {peek['metadatas'][i]}")
            else:
                print("  (Empty)")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_db()
