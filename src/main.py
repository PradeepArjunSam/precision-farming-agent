import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.core import AgentRuntime
from src.tools.scraper import ScraperTool
from src.tools.retriever import RetrieverTool

def main():
    print("Initializing Precision Farming Agent...")
    
    # Initialize Tools
    scraper = ScraperTool(whitelist=["fao.org", "usda.gov"])
    retriever = RetrieverTool(db_path="D:\\precision_farming\\data\\chroma")
    
    # Initialize Agent
    agent = AgentRuntime(
        tools=[scraper, retriever],
        model_path="D:\\AI_Models\\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    )
    
    print("Agent Ready.")
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"Query: {query}")
        result = agent.execute(query)
        print("Result:", result)
    else:
        print("Usage: python src/main.py <query>")

if __name__ == "__main__":
    main()
