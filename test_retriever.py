from src.tools.retriever import RetrieverTool
import shutil
import os

def test_retriever():
    print("Testing Retriever Tool...")
    
    # Use a test DB path (cleanup before test)
    test_db_path = "D:\\precision_farming\\data\\test_chroma"
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    
    retriever = RetrieverTool(db_path=test_db_path)
    
    # 1. Test Ingestion
    print("\n[Step 1] Ingesting test documents...")
    docs = [
        {
            "text": "Tomato seedlings need 14-16 hours of light per day for optimal growth.",
            "metadata": {"source": "fao.org", "topic": "light"}
        },
        {
            "text": "The ideal temperature for tomato germination is 20-25 degrees Celsius.",
            "metadata": {"source": "usda.gov", "topic": "temperature"}
        },
        {
            "text": "Wheat requires less water than rice during the vegetative stage.",
            "metadata": {"source": "icar.org.in", "topic": "water"}
        }
    ]
    
    try:
        retriever.add_documents(docs)
        print("[OK] Documents added.")
    except Exception as e:
        print(f"[FAIL] Ingestion failed: {e}")
        return

    # 2. Test Retrieval (Match)
    query = "How much light do tomatoes need?"
    print(f"\n[Step 2] Querying: '{query}'")
    result = retriever.run(query, n_results=1)
    
    top_doc = result['documents'][0]
    print(f"Top Result: {top_doc['text']}")
    
    if "14-16 hours" in top_doc['text']:
        print("[OK] Correct document retrieved.")
    else:
        print("[FAIL] Retrieved incorrect document.")

    # 3. Test Retrieval (Different Topic)
    query2 = "temperature for germination"
    print(f"\n[Step 3] Querying: '{query2}'")
    result2 = retriever.run(query2, n_results=1)
    print(f"Top Result: {result2['documents'][0]['text']}")
    
    if "20-25 degrees" in result2['documents'][0]['text']:
        print("[OK] Correct document retrieved.")
    else:
        print("[FAIL] Retrieved incorrect document.")

if __name__ == "__main__":
    test_retriever()
