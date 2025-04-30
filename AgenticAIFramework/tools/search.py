# tools/search.py
from tools.base import Tool

class Search(Tool):
    """Tool: Search - Simulates a web search and returns dummy URLs."""
    name = "search"
    inputs = ["query"]
    returns = {"results": "list of URLs"}

    def run(self, context):
        """Returns a mocked URL containing the search query."""
        query = context.get("query", "")
        return {"results": [f"https://example.com/search?q={query}"]}
