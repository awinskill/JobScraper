# planner.py
from openai import OpenAI
import json


def build_ranked_planner_prompt(goal, tool_descriptions):
    return f"""
You are a planning assistant.
Your goal: \"{goal}\"

You have access to the following tools:
{json.dumps(tool_descriptions, indent=2)}

Create a JSON plan where each step contains:
- tool: tool name
- input: dict of parameters (use {{prev_step.output_key}} if dependent)
- output_key: variable name to store result
"""


def call_llm_for_plan(llm, prompt):
    response = llm.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)
