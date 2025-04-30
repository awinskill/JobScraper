# tools/extract_jobs.py
from tools.base import Tool
from bs4 import BeautifulSoup
from models.job import Job

class ExtractJobs(Tool):
    """Tool: ExtractJobs - Parses HTML and extracts LinkedIn job data into Job objects."""
    name = "extract_jobs"
    inputs = ["html"]
    returns = {"jobs": "list of Job objects"}

    def run(self, context):
        """Parses LinkedIn job listing HTML and returns a structured list of Job objects."""
        soup = BeautifulSoup(context["html"], "html.parser")
        jobs = []

        for card in soup.select("li.jobs-search-results__list-item"):
            title = card.select_one("h3") and card.select_one("h3").text.strip()
            company = card.select_one("h4") and card.select_one("h4").text.strip()
            link = card.find("a", href=True)
            job_id = card.get("data-entity-urn", "")
            location = card.select_one(".job-search-card__location")
            date = card.select_one("time") and card.select_one("time").get("datetime")

            if title and company and link:
                job = Job(
                    linkedin_id=job_id,
                    title=title,
                    company=company,
                    location=location.text.strip() if location else None,
                    date=date,
                    url=link["href"]
                )
                jobs.append(job)

        return {"jobs": jobs}