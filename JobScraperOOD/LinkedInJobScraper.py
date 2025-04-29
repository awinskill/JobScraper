from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

import requests
import logging
import sys
import configparser

from argparse import ArgumentParser

import backoff  

from job_scraper import Job
from job_scraper import SearcherImplementation

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random

# Default HTTP settings for get_response
http_max_tries = 8
http_max_time=60




class LinkedInJobScraper(SearcherImplementation):
    """
    LinkedInJobScraper is a class that implements the SearcherImplementation interface
    for scraping job listings from LinkedIn.
    """
    def scrape(self) -> list[Job]:  

        self.__session.auth = (self.__username, self.__password)

        # Make a GET request to the LinkedIn page using the session
        # Use the session to make the request
        logging.debug("Getting search page response")

        search_page = self._get_response(self.__linkedin_url)
        if search_page.status_code == 429:
            raise requests.exceptions.RequestException("Rate limit exceeded")

        # Check if the request was successful (status code 200)
        if search_page.status_code != 200:
            logging.error("Failed to retrieve the page")
            sys.exit(0)

        soup = BeautifulSoup(search_page.content, "html.parser")

        logging.debug("Got the LinkedIn page")
        jobs = self.job_extractor(soup)
        return jobs

    # LinkedIn div class id that identifies the job card
    __job_string="base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card"


    # inject a custome function to extract jobs or use the default
    def __init__(self, configParser, parser, job_extractor=None):

        self.source="LinkedIn"

            # Check if the parameters were passed, and set the access variables
        if parser.parse_args().username:
            self.__username = parser.parse_args().username
        else:
            self.__username = configParser["LinkedIn"]["LINKEDIN_USERNAME"]
                                        
        if parser.parse_args().password:
            self.__password = parser.parse_args().password
        else:
            self.__password = configParser["LinkedIn"]["LINKEDIN_PASSWORD"]

        if parser.parse_args().url:
            self.__linkedin_url = parser.parse_args().url
        else:
            self.__linkedin_url = configParser["LinkedIn"]["LINKEDIN_BASE_URL"]
            self.__time_range = configParser["LinkedIn"]["LINKEDIN_TIME_FILTER"]

            if self.__time_range is not None:
                logging.info(f"Time range. Jobs posted in the last {self.__time_range} minutes")
                self.__time_range = int(self.__time_range) * 60 # convert to seconds

        # Check if the time range was passed, and set the access variables
            if self.__linkedin_url is not None:
                self.__linkedin_url = self._get_linkedin_url(self.__linkedin_url, self.__time_range)
                self.__linkedin_url = self.__linkedin_url.replace("\"","")
                logging.info(f"LinkedIn URL: {self.__linkedin_url}")
            else:
                logging.error("Unable to load LINKEDIN_URL")
                return None

        logging.info(f"Setting up LinkedIn HTTP Connection Pool")

        self.__session = requests.Session()

         # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=2,  # Number of connection pools
            pool_maxsize=10,      # Maximum number of connections in the pool
            max_retries=Retry(
                total=5,          # Retry up to 5 times for failed requests
                backoff_factor=0.3,  # Wait time between retries (exponential backoff)
                status_forcelist=[429, 500, 502, 503, 504]  # Retry on these HTTP status codes
            )
        )
        self.__session.mount("http://", adapter)
        self.__session.mount("https://", adapter)

        logging.info(f"Search URL {self.__linkedin_url}")

        # If the job_extractor is not injected, use the default extractor
        self.job_extractor = job_extractor or self._default_job_extractor

# CLEAN UP
    def __del__(self):
        logging.info("Cleaning up LinkedInJobScraper")
        self.__session.close()


    def _default_job_extractor(self, soup):
        logging.info("Extracting jobs with default extractor")
        return self._extract_jobs(soup)



    def _get_linkedin_url(self, base_url, time_range):
            # Parse the base URL
        url_parts = urlparse(base_url)
        query_params = parse_qs(url_parts.query)

        # Add or update the f_TPR parameter
        query_params["f_TPR"] = [time_range]

        # Rebuild the URL with the updated query parameters
        updated_query = urlencode(query_params, doseq=True)
        self.__linkedin_url = urlunparse((
            url_parts.scheme,
            url_parts.netloc,
            url_parts.path,
            url_parts.params,
            updated_query,
            url_parts.fragment
        ))

        return self.__linkedin_url

    


# Gets the response object from the URL, & handles the rate limit
# This function will retry the request if it fails due to a rate limit
# It will use the backoff library to retry the request
# The backoff library will retry the request with an exponential backoff
# The max_tries parameter will set the maximum number of retries
# The max_time parameter will set the maximum time to wait for the request

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
    def _get_response(self, url):
        logging.info(f"Getting response from {url}")
        response = self.__session.get(url)
        if response.status_code == 429:
            time.sleep(30)  # Wait for 30 seconds before retrying
            logging.error("LinkedIn Rate limit exceeded. Retrying after 30 seconds.")
            raise requests.exceptions.RequestException("Rate limit exceeded")

        if response.status_code == 200:
            logging.debug("HTTP Response: returning valid response")
            return response
        
        logging.error("Failed with status code: %s", response.status_code)
        return None



# Extract job details from the LinkedIn page
# The soup object will be passed to this function
    def _extract_jobs(self, soup):
        logging.debug(">")
        # job_string = "scaffold-layout__list "
        logging.debug(f"Extracting jobs with {self.__job_string}")
        job_elements = soup.find_all('div', {'class': self.__job_string})
        
        jobs = []
        for job_element in job_elements:
            logging.debug(">")
            job_element = self._extract_job_details(job_element)
            jobs.append(job_element)
        
        logging.debug(f"Found {len(jobs)} jobs")
        return jobs

    def _extract_jobs_threaded(self, soup):
        logging.info("Extracting jobs with multi-threading")
        job_elements = soup.find_all('div', {'class': self.__job_string})
        
        jobs = []

        # Use ThreadPoolExecutor to process job elements concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:  # Adjust max_workers based on your system
            future_to_job = {executor.submit(self._extract_job_details, job_element): job_element for job_element in job_elements}

            for future in as_completed(future_to_job):
                try:
                    job = future.result()  # Get the result of the job processing
                    if job is not None:
                        jobs.append(job)
                        time.sleep(random.uniform(1,3)) # Random sleep between 1 and 3 seconds
                except Exception as e:
                    logging.error(f"Error processing job element: {e}")

        logging.debug(f"Found {len(jobs)} jobs")
        return jobs

# Function to extract job details from a job element (job card on LinkedIn)
    def _extract_job_details(self, job_element):
        
        url = job_element.find('a')['href']
    
        # Get the job description page
        if url is not None:
            job_details = self._get_job_description_page(url)
            return Job(source="LinkedIn", url=url, raw_description=job_details)
        
        return None
    

    def _get_job_description_page(self, url):
        try:
            description_page = self._get_response(url)
            return description_page.content

        except requests.exceptions.ConnectionError as e:
            logging.error("Connection error while fetching job description: %s", e)        
        except requests.exceptions.RequestException as e:
            logging.error("Error accessing page %s", e)

        logging.error("Failed to retrieve job description page. Status code: %s",description_page.status_code)   

        return None





def main():
    print("Starting LinkedIn Job Scraper test framework...")

    # Set up logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    
    # Load configuration
    config = configparser.RawConfigParser()
    config.read("config.ini")  # Ensure you have a `config.ini` file with LinkedIn credentials and URL

    # Check if the configuration file is loaded
    if not config.sections():
        logging.error("Failed to load configuration file.")
        sys.exit(1)

    # Initialize argument parser
    
    parser = ArgumentParser(description="LinkedIn Job Scraper")
    parser.add_argument("--username", help="LinkedIn username")
    parser.add_argument("--password", help="LinkedIn password")
    parser.add_argument("--url", help="LinkedIn job search URL")
    
    parser.parse_args()

    # Initialize the LinkedInJobScraper
    try:
        print("Initializing LinkedInJobScraper...")
        scraper = LinkedInJobScraper(config, parser)
    except Exception as e:
        logging.error("Failed to initialize LinkedInJobScraper: %s", e)
        sys.exit(1)

    # Start scraping
    try:
        logging.debug("Starting job scraping...")
        jobs = scraper.scrape()
        logging.debug(f"Scraping completed. Found {len(jobs)} jobs.")

        # Print job details (for testing purposes)

        for job in jobs:
            print(job.title)  # Assuming the `Job` class has a `__str__` or `__repr__` method
    except Exception as e:
        logging.error("An error occurred during scraping: %s", e)
        sys.exit(1)


def custom_job_extractor(soup):
    # Custom job extraction logic
    logging.info("Custom job extraction logic")
    # This is a placeholder so we can change how the job is extracted e.g. using trafilatura rather than BeautifulSoup
    return None

if __name__ == "__main__":
    main()