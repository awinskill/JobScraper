import configparser
import logging

# Base class for searcher implementations
from abc import ABC, abstractmethod



class Job:
    def __init__(self, id=None, title=None, company=None, location=None, date=None, url=None, salary=None, salary_lower=None, salary_upper=None,description=None, summary=None, fit=None, raw_description=None):
        self.id = id
        self.url = url
        self.title = title
        self.company = company
        self.location = location
        self.date = date
        self.url = url
        self.salary = salary
        self.salary_lower = salary_lower
        self.salary_upper = salary_upper
        self.description = description
        self.summary = summary
        self.fit = fit
        self.raw_description = raw_description

    def __str__(self):
        return f"ID: {self.id},Title: {self.title}, Company: {self.company}, Location: {self.location}, \
            Date: {self.date}, URL: {self.url}, Salary: {self.salary}, \
                Salary_Lower: {self.salary_lower}, Salary_Upper: {self.salary_upper}, \
                    Description: {self.description}, Summary: {self.summary}, Fit: {self.fit}"
    def __repr__(self):    
        return f"ID: {self.id},Title: {self.title}, Company: {self.company}, Location: {self.location}, \
            Date: {self.date}, URL: {self.url}, Salary: {self.salary}, \
                Salary_Lower: {self.salary_lower}, Salary_Upper: {self.salary_upper}, \
                    Description: {self.description}, Summary: {self.summary}, Fit: {self.fit}"
    
 # Add this method to convert the object to a dictionary to enable serialization into JSON
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "date": self.date,
            "url": self.url,
            "salary": self.salary,
            "salary_lower": self.salary_lower,
            "salary_upper": self.salary_upper,
            "description": self.description,
            "summary": self.summary,
            "fit": self.fit,
            "raw_description": self.raw_description
        }


class ResumeProvider:
    def get_resume(self) -> str:
        return "Your resume text here"




class GenAISummarizer(ABC):
    @abstractmethod
    def summarize(self, job: Job) -> str:
        pass



class SearcherImplementation:
    def __init__(self):
        pass

    @abstractmethod
    def scrape(self) -> list[Job]:
        # Implement the scraping logic here
        pass

# class to sort a job list
class JobSorter(ABC):
    @abstractmethod
    def sort(self, jobs: list[Job]) -> list[Job]:
        #implementation of the sort
        pass

class SalaryDownJobSorter(JobSorter):
    def sort(self, jobs: list[Job]) -> list[Job]:
       sorted_jobs = sorted(jobs, key=lambda job: job.salary_upper or 0, reverse=True)

       return sorted_jobs


# output a job to a file or database
# This is an abstract base class for job writers    
class JobWriter(ABC):
    @abstractmethod
    def write(self, job: Job) -> None:
        # Implement the logic to write the job to a file or database
        pass

class DebugJobWriter(JobWriter):
    def write(self, job: Job) -> None:
        # Implement the logic to write the job to a file or database
        logging.info(f"Writing job to debug output: ")
        logging.info(f"Job title: {job.title}")
        logging.info(f"Company: {job.company}")

class TSVJobWriter(JobWriter):
    def __init__(self, filename: str):
        self.filename = filename
        # write the header to the file
        with open(self.filename, "w") as f:
            f.write("ID\tTitle\tCompany\tLocation\tDate\tSalary\tSalary_Lower\tSalary_Upper\tSummary\tDescription\tURL\tFit\n")


    def write(self, job: Job) -> None:
        # Implement the logic to write the job to a TSV file
        with open(self.filename, "a") as f:
            f.write(f"{job.id}\t{job.title}\t{job.company}\t{job.location}\t{job.date}\t{job.salary}\t{job.salary_lower}\t{job.salary_upper}\t{job.summary}\t{job.description}\t{job.url}\t{job.fit}\n")

class JobScraper:
    def __init__(self, scraper: SearcherImplementation):
        self.scraper = scraper
        
    def fetch_job_listings(self) -> list[Job]:
        # Use BeautifulSoup or requests to scrape jobs
        # return [Job(title="Software Engineer", url="http://example.com/job1")]
        jobs = self.scraper.scrape()
        return jobs
        
    
    def fetch_job_details(self, job: Job) -> None:
        # Update job.description with full job info
        # Do any local processing of the raw job description here
        logging.debug(f"Fetching job details for {job.title}")

# The class that orchestrates the job scraping and summarization process
class JobProcessor:
    def __init__(self, scraper: JobScraper, summarizer: GenAISummarizer, resume_provider: ResumeProvider, job_writer: JobWriter):
        self.scraper = scraper
        self.summarizer = summarizer
        self.resume_provider = resume_provider
        self.job_writer = job_writer

    def process_jobs(self) -> list[Job]:
        resume = self.resume_provider.get_resume()
        jobs = self.scraper.fetch_job_listings()

        job_list = []
        for job in jobs:
            self.scraper.fetch_job_details(job)
            # need to hook up the "resume provider" to the summarizer at some point in the future
            json_job = self.summarizer.summarize(job.raw_description)
            if json_job is None:
                logging.error("Failed to summarize job description")

            job_list.append(json_job)
        
        logging.info(f"Pre-sort job list {len(job_list)}")
           # Filter out None values
        job_list = [job for job in job_list if job is not None]
        logging.info(f"Filtered for null {len(job_list)}")

        job_list = SalaryDownJobSorter().sort(job_list)
        logging.info(f"Post-sort job list {len(job_list)}")

        for job in job_list:
            self.job_writer.write(job)

        return job_list

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting Job Scraper test framework...")
  