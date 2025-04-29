from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

import requests
import logging
import sys
import configparser
import re

from argparse import ArgumentParser

import backoff  

from job_scraper import Job
from job_scraper import SearcherImplementation

# Need to use Selenium & Edge due to Dice dynamic loading
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import time


# Default HTTP settings for get_response
http_max_tries = 8
http_max_time=60

MAX_WAIT_TIME=120


class DiceJobScraper(SearcherImplementation):

    def __init__(self, configParser, parser):

        self.source="Dice"


            # Check if the parameters were passed, and set the access variables
        if parser.parse_args().username:
            self.__username = parser.parse_args().username
        else:
            self.__username = configParser["Dice"]["DICE_USERNAME"]
                                        
        if parser.parse_args().password:
            self.__password = parser.parse_args().password
        else:
            self.__password = configParser["Dice"]["DICE_PASSWORD"]

        if parser.parse_args().url:
            self.url = parser.parse_args().url
        else:
            self.url = configParser["Dice"]["DICE_URL"]

            if self.url is not None:
                self.url = self.url.replace("\"","").replace("\'","")
            else:
                logging.error("Unable to load DICE_URL")
                return None

        self.__session = requests.Session()

        logging.debug(f"Search URL {self.url}")
        

    def scrape(self) -> list[Job]:
        super().scrape()

        self.__session.auth = (self.__username, self.__password)

        # Make a GET request to the LinkedIn page using the session
        # Use the session to make the request
        logging.debug("Getting search page response")

        job_list = self._get_response(self.url)
       
       # so we now have a list of Jobs - that have their source & URL attributes populated.
       # we need to get the raw job description so activities in the pipeline can process them

        for job in job_list:
            job.raw_description = self.get_job_description(job.url)

        return job_list





    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
    def get_job_description(self, url:str) -> str:
    
        url=url.replace("\"","").replace("\'","")

        print(f"**** Trying to access: {url}")

        response = self.__session.get(url)
        if response.status_code == 429:
            raise requests.exceptions.RequestException("Rate limit exceeded")

        if response.status_code == 200:
            logging.debug("HTTP Response: returning valid response")
            return response.content
        
        logging.error("Failed with status code: %s", response.status_code)
        return None







    # Gets the response object from the URL, & handles the rate limit
# This function will retry the request if it fails due to a rate limit
# It will use the backoff library to retry the request
# The backoff library will retry the request with an exponential backoff
# The max_tries parameter will set the maximum number of retries
# The max_time parameter will set the maximum time to wait for the request

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
    def _get_response(self, url) -> list[Job]:
     #   response = self.__session.get(url)
    #    if response.status_code == 429:
   #         raise requests.exceptions.RequestException("Rate limit exceeded")

    #    if response.status_code == 200:
   #         logging.debug("HTTP Response: returning valid response")
  #          return response
        
 #       logging.error("Failed with status code: %s", response.status_code)
 #       return None
    
    # 🔧 Setup Edge options
        options = EdgeOptions()
        options.use_chromium = True
        options.headless = True  # Set to False if you want to see the browser
        options.add_argument("start-minimized")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        # 🚀 Launch Edge with Selenium
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=options)

        # 🎯 Target URL
      #  url = "https://www.dice.com/jobs?q=leader%20AI&location=Seattle,%20WA,%20USA&filters.postedDate=ONE"

        print("[*] Loading Dice job search page...")
        driver.get(self.url)

        # Default process to extract the job
        process = 0
       # ✅ Wait up to MAX_WAIT_TIME until job titles appear
        try:
            if '/platform/jobs' in self.url:
                WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div[data-testid="jobSearchResultsContainer"]')
                    )
                )
                process = 2
            else:
                WebDriverWait(driver, MAX_WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-cy='card-title-link']"))
                )
                process=1
        except:
            print("[-] Timeout: Job listings did not load. Testing for redirect")
            if "/platform/jobs" in driver.current_url:
                 print("[-] Redirect detected. Switching to alternate processing")
                 process=2
        
        # The results we will return
        job_list = []

        if process==1:                

            print("[*] In job processing algo 1")

            # 🧼 Grab full rendered HTML
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # 🔍 Find job cards
            job_cards = soup.find_all("dhi-search-card", attrs={"data-cy": "search-card"})

            print(f"[+] Found {len(job_cards)} jobs.")

            
            for card in job_cards:
                job_id = card.get("data-cy-value")

                if job_id is not None:
                    job_list.append(Job(id=job_id, source="Dice", url=f"https://www.dice.com/job-detail/{job_id}"))
            
            
        elif process==2:
            print("[*] In job processing algo 2")
            # Need to use Regex to get the jobID from the URL

            # we've gotten here so we know we've been redirected to the REACT site 
            # 🧼 Grab full rendered HTML
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

     
            # 🔍 Find job cards - this gets the search results
            search_results = soup.find("div", attrs={"data-testid": "jobSearchResultsContainer"})

            # now need to extract each link
            if search_results is not None:
                dice_job_list = search_results.find_all("a", attrs={"data-testid": "job-search-job-card-link"})

                for job in dice_job_list:
                    current_url=job['href']
                    current_id = re.findall(r"[^\/]{36}", current_url)
                    print(f"Current URL = {current_url}")
                    print(f"Job id = {current_id}")
                    job_list.append(Job(id=current_id, source="Dice",url=current_url))

        # Shutdown the browser    
        driver.quit()
        return job_list


    
