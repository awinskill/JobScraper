# tests/test_registry.py
import pytest
from registry import ToolRegistry
from tools.summarize import Summarize

def test_registry_register_and_run():
    registry = ToolRegistry(stats_file="/tmp/test_tool_stats.json")
    tool = Summarize()
    registry.register(tool)
    assert tool.name in registry.tools
    result = registry.run_tool("summarize", {"text": "This is a test."})
    assert "summary" in result

def test_registry_scoring():
    registry = ToolRegistry(stats_file="/tmp/test_tool_stats.json")
    tool = Summarize()
    registry.register(tool)
    registry.run_tool("summarize", {"text": "A second test."})
    stats = registry.tool_stats["summarize"]
    assert stats["successes"] >= 1