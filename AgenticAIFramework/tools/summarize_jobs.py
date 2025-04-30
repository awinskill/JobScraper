# tools/summarize_jobs.py

from tools.base import Tool

class SummarizeJobs(Tool):
    """Tool: SummarizeJobs - Uses GPT to summarize a list of job listings."""
    name = "summarize_jobs"
    inputs = ["jobs"]
    returns = {"summary": "string"}

    def run(self, context):
        """Summarizes the job data provided in the context using OpenAI's GPT-4."""
        import openai
        from openai import OpenAI

        jobs = context["jobs"]
        if not jobs:
            return {"summary": "No jobs to summarize."}

        job_text = "\n".join(
            f"{job['title']} at {job['company']} in {job['location']}" if isinstance(job, dict)
            else str(job)
            for job in jobs[:10]
        )

        prompt = f"Summarize the following job listings and suggest top matches:\n\n{job_text}"

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return {"summary": response.choices[0].message.content.strip()}
