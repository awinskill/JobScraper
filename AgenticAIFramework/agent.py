# agent.py
from registry import ToolRegistry
from planner import build_ranked_planner_prompt, call_llm_for_plan
from tools.search import Search
from tools.summarize import Summarize
from openai import OpenAI
import logging
import importlib
import json
import os

class Agent:
    def __init__(self, api_key, goal):
        self.goal = goal
        self.registry = ToolRegistry()
        self.plan = []
        self.context = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self._register_tools()
        self.api_key = api_key
        self.llm = OpenAI(api_key=self.api_key)

    def _register_tools(self):
        self.logger.info("Loading tools from config/tools.json...")
        with open("config/tools.json") as f:
            config = json.load(f)

        registered = {}
        pending = config[:]
        retries = 0

        while pending and retries < 3:
            next_pending = []
            for entry in pending:
                name = entry.get("name")
                module_name = entry.get("module")
                class_name = entry.get("class")
                enabled = entry.get("enabled", True)
                depends_on = entry.get("depends_on", [])

                if not enabled:
                    self.logger.info("Tool disabled: %s.%s", module_name, class_name)
                    continue

                if any(dep not in registered for dep in depends_on):
                    self.logger.info("Tool deferred due to unmet dependencies: %s", name)
                    next_pending.append(entry)
                    continue

                try:
                    module = importlib.import_module(module_name)
                    cls = getattr(module, class_name)
                    instance = cls()
                    self.registry.register(instance)
                    registered[name] = True
                    self.logger.info("Registered tool: %s", instance.name)
                except Exception as e:
                    self.logger.error("Failed to load tool %s.%s: %s", module_name, class_name, e)
            pending = next_pending
            retries += 1

        if pending:
            self.logger.warning("Some tools could not be registered due to unresolved dependencies: %s",
                                [tool.get("name") for tool in pending])
            

    def perceive(self):
        """Optional: Observe current state, context, or memory."""
        self.logger.info("Perceiving environment...")

    def plan_steps(self):
        """Use GPT to create a plan from the goal and available tools."""
        self.logger.info("Planning steps for goal: %s", self.goal)
        prompt = build_ranked_planner_prompt(self.goal, self.registry.describe_all_for_planner())
        self.logger.info("Generated prompt for planning: %s", prompt)
        self.logger.info("Calling LLM for plan...")
        self.plan = call_llm_for_plan(self.llm, prompt)
        self.logger.info("Plan generated: %s", self.plan)

    def act(self):
        """Execute each step in the plan using tools and update context."""
        self.logger.info("Executing plan...")
        for step in self.plan:
            self.logger.info("Running tool '%s' with input %s", step['tool'], step['input'])
            inputs = self._resolve_inputs(step['input'])
            result = self.registry.run_tool(step['tool'], inputs)
            self.context[step['output_key']] = result
            self.logger.info("Tool '%s' returned %s", step['tool'], result)

    def evaluate(self):
        """Optional: Evaluate outcome quality, score plan, or log insights."""
        self.logger.info("Evaluating results...")

    def learn(self):
        """Optional: Adjust strategy, tool preferences, or retry planning."""
        self.logger.info("Learning from experience...")

    def run(self):
        self.logger.info("Starting agent lifecycle for goal: '%s'", self.goal)
        self.perceive()
        self.plan_steps()
        self.act()
        self.evaluate()
        self.learn()
        self.logger.info("Agent run completed.")

    def _resolve_inputs(self, input_map):
        resolved = {}
        for k, v in input_map.items():
            if isinstance(v, str) and v.startswith("{{"):
                expr = v.strip("{} ")
                try:
                    resolved[k] = eval(expr, {}, self.context)
                except Exception as e:
                    raise ValueError(f"Failed to resolve input '{{v}}': {e}")
            else:
                resolved[k] = v
        return resolved