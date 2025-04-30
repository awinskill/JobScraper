# tools/base.py
import json

class Tool:
    """Base class for all tools with dynamic description loading and optional scoring."""
    name = ""
    inputs = []
    returns = {}

    def run(self, context):
        """Override this method in subclasses to perform the tool's main task."""
        raise NotImplementedError

    def on_success(self, result):
        """Optional callback for when a tool executes successfully.

        Returns a dict with metadata such as scoring.
        """
        return {}

    def on_failure(self, error):
        """Optional callback for when a tool fails to execute.

        Returns a dict with metadata such as error messages or penalties.
        """
        return {"penalty": 0.1, "error": str(error)}

    @property
    def description(self):
        """Fetch this tool's description dynamically from tools.json."""
        return get_tool_description(self.name)


def get_tool_description(name):
    """Helper function to extract a tool's description from the config file."""
    try:
        with open("config/tools.json") as f:
            tools = json.load(f)
        for tool in tools:
            if tool.get("name") == name:
                return tool.get("description", "No description available.")
    except Exception:
        pass
    return "No description available."