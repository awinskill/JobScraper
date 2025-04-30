# main.py
from agent import Agent
import configparser

# Load configuration
config = configparser.RawConfigParser()
config.read('../config.ini')
api_key = config.get('OpenAI', 'OPENAI_API_KEY')
goal = "Find recent articles about AI agents and summarize them"
agent = Agent(api_key, goal)
agent.run()
