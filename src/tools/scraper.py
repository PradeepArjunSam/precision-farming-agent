from typing import Dict, Any, List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base import BaseTool

class ScraperTool(BaseTool):
    # Strict Whitelist
    DEFAULT_WHITELIST = [
        "fao.org",
        "usda.gov",
        "icar.org.in",
        "ipm.ucanr.edu",
        "extension.psu.edu",
        "cals.cornell.edu",
        "extension.org",
        "garden.org",
        ".edu",
        ".ac.uk"
    ]

    def __init__(self, whitelist: List[str] = None, allow_any: bool = False):
        self.whitelist = whitelist if whitelist else self.DEFAULT_WHITELIST
        self.allow_any = allow_any
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "PrecisionFarmingAgent/1.0 (Research Purpose; +http://github.com/example/bot)"
        })

    @property
    def name(self) -> str:
        return "scraper_tool"

    @property
    def description(self) -> str:
        return (
            "Fetches content from approved agricultural institutions. "
            "Input: 'url' string. Returns: {'content': text, 'metadata': dict} or error."
        )

    def _is_whitelisted(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower()
            if self.allow_any:
                return True
            # Handle subdomains, e.g., www.fao.org matches fao.org
            return any(domain.endswith(allowed) or domain == allowed for allowed in self.whitelist)
        except Exception:
            return False

    def run(self, url: str) -> Dict[str, Any]:
        """
        Fetches and cleans text from the URL if it is in the whitelist.
        """
        if not self._is_whitelisted(url):
            return {
                "status": "error",
                "message": f"URL refused: Domain not in trusted whitelist. Allowed: {self.whitelist}"
            }

        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Basic validation: If text is too short, might be a failed scrape (e.g. JS only)
            if len(text) < 100:
                 return {
                    "status": "warning",
                    "message": "Content too short, page might be JavaScript rendered.",
                    "content": text,
                    "metadata": {"url": url}
                }

            return {
                "status": "success",
                "content": text,
                "metadata": {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "length": len(text)
                }
            }

        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Fetch failed: {str(e)}"
            }
