# registry.py
from collections import defaultdict
import json, os
from datetime import datetime
from datetime import timezone

class ToolRegistry:
    def __init__(self, stats_file="data/tool_stats.json"):
        self.tools = {}
        self.tool_stats = defaultdict(lambda: {
            "successes": 0, "failures": 0, "quality_scores": [], "last_used": None
        })
        self.stats_file = stats_file
        self._load_stats()

    def register(self, tool):
        self.tools[tool.name] = tool

    def get_tool(self, name):
        return self.tools.get(name)

    def run_tool(self, name, context):
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")
        try:
            result = tool.run(context)
            feedback = tool.on_success(result)
            self.record_success(name, feedback)
            return result
        except Exception as e:
            feedback = tool.on_failure(e)
            self.record_failure(name, feedback)
            raise

    def record_success(self, name, feedback):
        s = self.tool_stats[name]
        s["successes"] += 1
        s["last_used"] = datetime.now(timezone.utc).isoformat()
        if "quality_score" in feedback:
            s["quality_scores"].append(feedback["quality_score"])
        self._save_stats()

    def record_failure(self, name, feedback):
        s = self.tool_stats[name]
        s["failures"] += 1
        s["last_used"] = datetime.utcnow().isoformat()
        self._save_stats()

    def _save_stats(self):
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
        with open(self.stats_file, "w") as f:
            json.dump(self.tool_stats, f, indent=2)

    def _load_stats(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r") as f:
                raw = json.load(f)
                for name, stats in raw.items():
                    self.tool_stats[name] = stats

    def describe_all_for_planner(self):
        tools = []
        for name, tool in self.tools.items():
            s = self.tool_stats[name]
            total = s["successes"] + s["failures"]
            avg = sum(s["quality_scores"]) / len(s["quality_scores"]) if s["quality_scores"] else 0.0
            rate = s["successes"] / total if total > 0 else 0.0
            tools.append({
                "name": name,
                "description": tool.description,
                "inputs": tool.inputs,
                "returns": tool.returns,
                "score": round(avg, 2),
                "success_rate": round(rate, 2),
                "rank_hint": "high" if avg >= 0.7 else "medium" if avg >= 0.4 else "low"
            })
        return tools