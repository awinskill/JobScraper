from bs4 import BeautifulSoup
import requests
import re
import logging
import backoff
import cloudscraper
import certifi

from job_scraper import SearcherImplementation
from job_scraper import Job

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time


# Default HTTP settings for get_response
http_max_tries = 8
http_max_time=60


class IndeedJobScraper(SearcherImplementation):

    def __init__(self, configParser, parser):
     

        # Check if the parameters were passed, and set the access variables
        if parser.parse_args().username:
            self.__username = parser.parse_args().username
        else:
            self.__username = configParser["Indeed"]["INDEED_USERNAME"]
                                        
        if parser.parse_args().password:
            self.__password = parser.parse_args().password
        else:
            self.__password = configParser["Indeed"]["INDEED_PASSWORD"]

        if parser.parse_args().url:
            self.__indeed_url = parser.parse_args().url
        else:
            self.__indeed_url = configParser["Indeed"]["INDEED_URL"]

            if self.__indeed_url is not None:
                self.__indeed_url = self.__indeed_url.replace("\"","")
            else:
                logging.error("Unable to load INDEED_URL")
                return None

        self.__session = requests.Session()
        self.__indeed_url = self.__indeed_url.strip("'\"")

        logging.debug(f"Search URL {self.__indeed_url}")


    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
    def scrape(self) -> list[Job]:  
        self.__session.auth = (self.__username, self.__password)

        print("******* Indeed Scraper Started **********")
        # Example usage
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }

        # Setup headless Chrome
        
        options = Options()
        options.headless = True  # Set False if you want to watch the browser
        options.use_chromium = True
        options.add_argument("start-maximized")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        
        # Launch browser
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

        driver.get(self.__indeed_url)
    
        # Wait for dynamic content to load
        time.sleep(5)

        # Grab HTML after rendering
        html = driver.page_source
        recent_jobs = self.extract_recent_jobs(html)
        return recent_jobs
        
        

    def is_posted_within_last_hour(self, posted_text):
        posted_text = posted_text.lower().strip()
        if "just posted" in posted_text:
            return True
        match = re.match(r"(\d+)\s+(minute|minutes)\s+ago", posted_text)
        if match and int(match.group(1)) <= 60:
            return True
        return False

    def extract_recent_jobs(self, html):

        soup = BeautifulSoup(html, "html.parser")
        job_cards = soup.find_all("div", class_="job_seen_beacon")  # or whatever class wraps the job

        recent_jobs = []
        for card in job_cards:
            # You'll need to inspect the correct class for the posted time span
            time_span = card.find("span", class_="date")  # Sometimes it's "date" or similar
            if time_span and is_posted_within_last_hour(time_span.get_text()):
                title_elem = card.find("h2")  # Or appropriate title tag
                job_title = title_elem.get_text(strip=True) if title_elem else "Unknown title"
                recent_jobs.append(job_title)

        return recent_jobs
    
    def get_indeed_page(self, url) -> str:
        response = self.__session.get(url)
        if response.status_code == 429:
            raise requests.exceptions.RequestException("Rate limit exceeded")

        if response.status_code == 200:
            logging.debug("HTTP Response: returning valid response")
            return response
        
        logging.error("Failed with status code: %s", response.status_code)
        return None
    

    
