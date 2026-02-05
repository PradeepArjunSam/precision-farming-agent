from typing import Dict, Any, List
from duckduckgo_search import DDGS
from .base import BaseTool
from .scraper import ScraperTool

class SearchTool(BaseTool):
    def __init__(self):
        # Allow scraping any URL found by search
        self.scraper = ScraperTool(allow_any=True)
        self.ddgs = DDGS()

    @property
    def name(self) -> str:
        return "search_tool"

    @property
    def description(self) -> str:
        return (
            "Searches the web for information. "
            "Input: 'query' string. Returns: {'content': combined_text, 'sources': list}."
        )

    def run(self, query: str) -> Dict[str, Any]:
        # Enforce Whitelist: Append site:domain1 OR site:domain2...
        # This ensures DuckDuckGo ONLY returns results from approved sources
        whitelist_operators = " OR ".join([f"site:{d}" for d in self.scraper.whitelist])
        strict_query = f"{query} ({whitelist_operators})"
        
        print(f"  > Searching web (Strict): {strict_query[:50]}...")
        
        try:
            # 1. Search (Limit to 3 results)
            results = list(self.ddgs.text(strict_query, max_results=3))
            
            combined_content = ""
            sources = []
            
            if not results:
                 return {
                    "status": "warning",
                    "message": "No results found."
                }

            # 2. Scrape Top Results
            for res in results:
                url = res['href']
                print(f"  > Found URL: {url}")
                
                # Check whitelist via scraper (optional, or we can relax it for search)
                # For now, let's allow search to find valid domains or maybe just try to scrape
                # We will temporarily bypass strict whitelist for search results or check if it matches
                
                # Try to scrape
                scrape_res = self.scraper.run(url)
                
                if scrape_res.get("status") == "success":
                   text = scrape_res.get("content", "")[:2000] # Limit context window
                   combined_content += f"Source: {url}\nTitle: {res['title']}\nContent: {text}\n\n"
                   sources.append(url)
                else:
                    # Fallback to snippet if scrape fails
                    combined_content += f"Source: {url}\nTitle: {res['title']}\nSnippet: {res['body']}\n\n"
                    sources.append(url)
            
            return {
                "documents": [
                    {
                        "text": combined_content, 
                        "metadata": {"source": "web_search", "query": query}
                    }
                ],
                "sources": sources
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}"
            }
