import job_scraper
import LinkedInJobScraper
import configparser
from argparse import ArgumentParser
import logging
import ai_summarizer
"""
def main():

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Starting LinkedIn Job Scraper test framework...")


    config = configparser.RawConfigParser()
    config.read("config.ini")  # Ensure you have a `config.ini` file with LinkedIn credentials and URL


    # Check if the configuration file is loaded
    if not config.sections():
        logging.error("Failed to load configuration file.")
        sys.exit(1)

    
    logging.info("Loaded configuration file...")

    parser = ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument("--username", help="LinkedIn username")
    parser.add_argument("--password", help="LinkedIn password")
    parser.add_argument("--url", help="LinkedIn job search URL")
    parser.parse_args()
    
    logging.debug("Parsed command line arguments...")
    logging.debug("Running LinkedInJobScraper...")

    # Initialize the LinkedInJobScraper
    # Injecting the LinkedInJobScraper into the JobScraper
    scraper = job_scraper.JobScraper( LinkedInJobScraper.LinkedInJobScraper(config, parser) )

    jobs = scraper.fetch_job_listings()
    logging.debug(f"Finished scraping job listings...{len(jobs)} jobs found")
    # Initialize the AI summarizer
    summarizer = ai_summarizer.OpenAISummarizer(config, "prompt.txt")
    logging.debug("Initialized AI summarizer...")
   
    # Summarize the job description
    for job in jobs:
        logging.debug(f"Summarizing")
        json_job = summarizer.summarize(job.raw_description)

        logging.debug("Summarized job description...")
        # Print the summarized job
        print(json_job.title)
        logging.debug("Finished summarizing job description...")

"""

def main():

    # setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Starting LinkedIn Job Scraper test framework...")

    # load configuration
    config = configparser.RawConfigParser()
    config.read("config.ini")  # Ensure you have a `config.ini` file with LinkedIn credentials and URL


    # Check if the configuration file is loaded
    if not config.sections():
        logging.error("Failed to load configuration file.")
        sys.exit(1)

    
    logging.info("Loaded configuration file...")

    # Initialize argument parser
    parser = ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument("--username", help="LinkedIn username")
    parser.add_argument("--password", help="LinkedIn password")
    parser.add_argument("--url", help="LinkedIn job search URL")
    parser.parse_args()
    
    logging.info("Parsed command line arguments...")
    logging.info("Running LinkedInJobScraper...")

    job_processor = job_scraper.JobProcessor(
        scraper=job_scraper.JobScraper(LinkedInJobScraper.LinkedInJobScraper(config, parser)),
        summarizer=ai_summarizer.OpenAISummarizer(config, "prompt.txt"),
        resume_provider=job_scraper.ResumeProvider(), 
        job_writer=job_scraper.TSVJobWriter("jobs2.tsv")
    )
    logging.info("Initialized JobProcessor...")


    # Start the job processing
    logging.info("Starting job processing...")
    job_list = job_processor.process_jobs()
    logging.info("Finished job processing...")
    
    # Print the summarized job
    print(f"Found {len(job_list)} jobs")
  
    logging.info("Finished printing job summaries...")
    logging.info("Finished LinkedIn Job Scraper test framework...")
    


if __name__ == "__main__":
    main()

