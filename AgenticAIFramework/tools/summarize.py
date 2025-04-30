# tools/summarize.py
from tools.base import Tool

class Summarize(Tool):
    """Tool: Summarize - Condenses a block of text into a brief summary."""
    name = "summarize"
    inputs = ["text"]
    returns = {"summary": "string"}

    def run(self, context):
        """Returns a truncated version of the input text as a simple summary."""
        text = context.get("text", "")
        summary = "• " + " ".join(text.split()[:10]) + "..."
        return {"summary": summary}