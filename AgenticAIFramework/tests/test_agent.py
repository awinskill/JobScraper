# tests/test_agent.py
from agent import Agent

def test_agent_init():
    agent = Agent("Summarize text")
    assert agent.goal == "Summarize text"
    assert agent.registry is not None
    assert len(agent.registry.tools) > 0