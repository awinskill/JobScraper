from bs4 import BeautifulSoup

import requests
import logging
import sys
import configparser

from argparse import ArgumentParser

import backoff
from abc import ABC, abstractmethod
from job_scraper import Job
from job_scraper import SearcherImplementation

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
        jobs = self._extract_jobs(soup)
        return jobs

    # LinkedIn div class id that identifies the job card
    __job_string="base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card"


    def __init__(self, configParser, parser):


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
            self.__linkedin_url = configParser["LinkedIn"]["LINKEDIN_URL"]

            if self.__linkedin_url is not None:
                self.__linkedin_url = self.__linkedin_url.replace("\"","")
            else:
                logging.error("Unable to load LINKEDIN_URL")
                return None

        self.__session = requests.Session()

        logging.debug(f"Search URL {self.__linkedin_url}")





    


# Gets the response object from the URL, & handles the rate limit
# This function will retry the request if it fails due to a rate limit
# It will use the backoff library to retry the request
# The backoff library will retry the request with an exponential backoff
# The max_tries parameter will set the maximum number of retries
# The max_time parameter will set the maximum time to wait for the request

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
    def _get_response(self, url):
        response = self.__session.get(url)
        if response.status_code == 429:
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
            job_element = Job(raw_description = self._extract_job_details(job_element))
            jobs.append(job_element)
        
        logging.debug(f"Found {len(jobs)} jobs")
        return jobs

# Function to extract job details from a job element (job card on LinkedIn)
# This function will extract the job title, company, location, date, URL, salary, and description
    def _extract_job_details(self, job_element):
        
        url = job_element.find('a')['href']
    
        # Get the job description page
        if url is not None:
            job_details = self._get_job_description_page(url)
            return job_details
        
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

if __name__ == "__main__":
    main()