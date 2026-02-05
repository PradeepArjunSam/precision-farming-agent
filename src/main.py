import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.core import AgentRuntime
from src.tools.scraper import ScraperTool
from src.tools.retriever import RetrieverTool

def main():
    print("Initializing Precision Farming Agent...")
    
    # Initialize Tools
    from src.tools.search import SearchTool

    # Initialize Tools
    # Scraper with default whitelist (for direct URL scraping if needed)
    scraper = ScraperTool(whitelist=["fao.org", "usda.gov"])
    retriever = RetrieverTool(db_path="data/chroma")
    search = SearchTool() # Hybrid Search + Open Scraper
    
    # Initialize Agent
    agent = AgentRuntime(
        tools=[scraper, retriever, search],
        model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
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
