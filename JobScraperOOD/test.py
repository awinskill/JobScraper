import job_scraper
import LinkedInJobScraper
import IndeedJobScraper
import DiceJobScraper

from configparser import RawConfigParser
from argparse import ArgumentParser
import logging
import ai_summarizer
import anthropic_summarizer
from deepseek_summarizer import DeepseekSummarizer
import sys


def main():

    # setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Starting LinkedIn Job Scraper test framework...")

    # load configuration
    config_file = RawConfigParser()
    config_file.read("config.ini")  # Ensure you have a `config.ini` file with LinkedIn credentials and URL


    # Check if the configuration file is loaded
    if not config_file.sections():
        logging.error("Failed to load configuration file.")
        sys.exit(1)

    
    logging.info("Loaded configuration file...")

    # Initialize argument parser
    parser = ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument("--username", help="LinkedIn username")
    parser.add_argument("--password", help="LinkedIn password")
    parser.add_argument("--url", help="LinkedIn job search URL")
    parser.add_argument("--username2", help="Dice username")
    parser.add_argument("--password2", help="Dice password")
    parser.add_argument("--url2", help="Dice job search URL")
    parser.add_argument("--developer", help="Developer mode - limits number of jobs to scrape", action="store_true")
    parser.add_argument("--job_limt", help="Job limit for developer mode", type=int, default=2)
    
    parser.parse_args()
    
    logging.info("Parsed command line arguments...")
    logging.info("Running JobScraper...")

    linkedin_scraper = job_scraper.JobScraper(LinkedInJobScraper.LinkedInJobScraper(config_file, parser))
    dice_scraper = job_scraper.JobScraper(DiceJobScraper.DiceJobScraper(config_file, parser))
    summarizer = ai_summarizer.OpenAIStructuredSummarizer(config_file, "prompt.txt")
 #   summarizer = DeepseekSummarizer(config_file, "prompt.txt")
 #   summarizer = anthropic_summarizer.AnthropicSummarizer(config_file, "prompt.txt")
    tsv_job_writer = job_scraper.TSVJobWriter("jobs2.tsv")
    xl_job_writer = job_scraper.XLJobWriter("jobs2.xlsx")
    job_sorter = job_scraper.SalaryDownJobSorter()


#    job_processor = job_scraper.BasicJobProcessor(
#        scraper=scraper,
#        summarizer=summarizer,
#        resume_provider=job_scraper.ResumeProvider(), 
#        job_writer=job_writer
#    )
#    scrapers=[scraper, scraper2]
    
    scrapers= [linkedin_scraper, dice_scraper]
 
 #   writers=[job_writer, job_writer2]
    writers=[tsv_job_writer, xl_job_writer ]

    job_processor = job_scraper.JobMultiParallelProcessor(
        config=config_file,
        scrapers=scrapers,
        summarizer=summarizer,
        writers=writers,
        sorter=job_sorter
    )
 


    logging.info("Initialized JobProcessor...")


    # Start the job processing
    logging.info("Starting job processing...")
    job_list = job_processor.process_jobs()
    logging.info("Finished job processing...")
    
    # Print the summarized job
    print(f"Found {len(job_list)} jobs")
  
    logging.info("Finished printing job summaries...")
    logging.info("Finished Job Scraper test framework...")
    


if __name__ == "__main__":
    main()

