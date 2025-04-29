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

class LaddersJobScraper(SearcherImplementation):

    def __init__(self):


            # Check if the parameters were passed, and set the access variables
        if parser.parse_args().username:
            self.__username = parser.parse_args().username
        else:
            self.__username = configParser["Ladders"]["LADDERS_USERNAME"]
                                        
        if parser.parse_args().password:
            self.__password = parser.parse_args().password
        else:
            self.__password = configParser["Ladders"]["LADDERS_PASSWORD"]

        if parser.parse_args().url:
            self.__linkedin_url = parser.parse_args().url
        else:
            self.__linkedin_url = configParser["Ladders"]["LADDERS_URL"]

            if self.__linkedin_url is not None:
                self.__linkedin_url = self.__linkedin_url.replace("\"","")
            else:
                logging.error("Unable to load LADDERS_URL")
                return None

        self.__session = requests.Session()

        logging.debug(f"Search URL {self.__ladders_url}")
        

    def scrape(self) -> list[Job]:
        super().scrape()

         self.__session.auth = (self.__username, self.__password)

        # Make a GET request to the LinkedIn page using the session
        # Use the session to make the request
        logging.debug("Getting search page response")

        search_page = self._get_response(self.__ladders_url)
        if search_page.status_code == 429:
            raise requests.exceptions.RequestException("Rate limit exceeded")

        # Check if the request was successful (status code 200)
        if search_page.status_code != 200:
            logging.error("Failed to retrieve the page")
            sys.exit(0)

        soup = BeautifulSoup(search_page.content, "html.parser")

        logging.debug("Got the Ladders page")
        jobs = self._extract_jobs(soup)
        return jobs

    
    