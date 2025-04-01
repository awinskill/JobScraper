#######################################
## JobScrape.py - LinkedIn Job Scraper
#######################################

import re
import requests
import os
import backoff
import logging

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from argparse import ArgumentParser



# Load environment variables from .env file
load_dotenv()

### GLOBALS ###
# some globals to make the code cleaner
parser = ArgumentParser(description="LinkedIn Job Scraper")

# LinkedIn div class id that identifies the job card
job_string="base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card"
salary_string_collection=["main-job-card__salary-info block my-0.5 mx-0",
               "aside-job-card__salary-info","job-details-preferences-and-skills__pill"]

#salary_regex="\$\d\d\dK/yr\s+-\s+\$\d\d\dK/yr"
#salary_regex="\s+\$\d{1,3}K/yr\s+-\s+\$\d{1,3}K/yr\s+"
salary_regex=[r'\$\d{1,3},?\d{1,3}\s?-?\s?\$\d{1,3},?\d{1,3}', 
              r'\$\d{1,3},?\d{1,3}\s?to?\s?\$\d{1,3},?\d{1,3}',
              r'\$\d{1,3},?\d{1,3}.\d{1,2}\s?to?\s?\$\d{1,3},?\d{1,3}.\d{1,2}',
              r'\$\d{1,3},?\d{1,3}\s?—\s?\$\d{1,3},?\d{1,3}',
              r'\$\d{1,3},?\d{1,3}\s?\/year in our lowest geographic market up to\s?\$\d{1,3},?\d{1,3}',
                r'starting at \$\d{1,3},?\d{1,3}']

session = requests.Session()





# data class to hold the credentials
class Credentials:
    def __init__(self, username, password):
        self.username = username
        self.password = password

# data class to hold the job details
class Job:
    def __init__(self, title, company, location, date, url=None, salary=None, description=None):
        self.title = title
        self.company = company
        self.location = location
        self.date = date
        self.url = url
        self.salary = salary
        self.description = description


    def __str__(self):
        return f"Title: {self.title}, Company: {self.company}, Location: {self.location}, Date: {self.date}, URL: {self.url}, Salary: {self.salary}, Description: {self.description}"
    def __repr__(self):    
        return f"Title: {self.title}, Company: {self.company}, Location: {self.location}, Date: {self.date}, URL: {self.url}, Salary: {self.salary}, Description: {self.description}"

#################################################
## UTILITY FUNCTIONS
#################################################
# setup command line arguments
def setup_args():
    parser.add_argument("-u", "--username", help="LinkedIn username", required=False)
    parser.add_argument("-p", "--password", help="LinkedIn password", required=False)
    parser.add_argument("-l", "--url", help="LinkedIn URL", required=False)
    parser.add_argument("-o", "--output", help="Output file name", required=False, default="jobs.tsv")

# dumps the environment variables to the console
# This is useful for debugging purposes
def dump_env():
    print("LINKEDIN_USERNAME: ", os.getenv("LINKEDIN_USERNAME"))
    print("LINKEDIN_PASSWORD: ", os.getenv("LINKEDIN_PASSWORD"))
    print("LINKEDIN_URL: ", os.getenv("LINKEDIN_URL"))

# Function to set up the HTTP session
# This function will set up the session with the required headers and parameters
def setup_session():
    # Set the timeout to 5 seconds
    session.timeout = 5
    # Set the allow_redirects to False
    session.allow_redirects = False


# Gets the response object from the URL, & handles the rate limit
# This function will retry the request if it fails due to a rate limit
# It will use the backoff library to retry the request
# The backoff library will retry the request with an exponential backoff
# The max_tries parameter will set the maximum number of retries
# The max_time parameter will set the maximum time to wait for the request

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=8, max_time=30, logger=logging)
def get_response(url):
    response = session.get(url)
    if response.status_code == 429:
        raise requests.exceptions.RequestException("Rate limit exceeded")

    if response.status_code == 200:
        return response
    else:
        print(f"Failed with status code: {response.status_code}")
        return None
    

#################################################
## Functions help with debugging
#################################################

# Function to debug the salary extraction
# This function will write the job description to a file
def debug_salary_extract(url):
    # Get the job description page
    page = get_job_description_page(url)
    
    if page is not None:
        with open("job.txt", "a", encoding="utf-8") as file:
            file.write("@@@@ Start Job Description @@@@\n")
            file.write(page.prettify())  # Write the formatted HTML content to the file
            file.write("\n\n\n")  # Add some spacing between different job descriptions

# Helper function to print out all the jobs found
def print_jobs(jobs):
    for job in jobs:
        logging.debug(job)
        
# Helper function to print out all the jobs found
def print_job_titles(jobs):
    for job in jobs:
        logging.debug(job.title, end=", ")
        logging.debug(job.company)


#################################################
## Functions to get the salary in various ways
#################################################

def extract_salary_by_tag_collection(soup):
    for tag in salary_string_collection:
        logging.debug(f"Trying to extract salary by tag: {tag}")
        # Try to extract the salary using the current tag
        salary = extract_salary_by_tag(soup, tag)
        # loop until a salary is found, return on first found
        if salary is not None:
            return salary
        
    logging.debug("Salary not found for by tag collection")
    return None


def extract_salary_by_tag(page, tag):
    # Get the job description page
    # page = get_job_description_page(url)
    
    if page is not None:
        # Find the salary element by its tag name
        salary_element = page.find('div', {'class': tag})

        if salary_element is None:
            # If not found, try to find it by a different tag name
            # This is a fallback in case the salary is not found by the first tag
            salary_element = page.find('span', {'class': tag})
    
        if salary_element is not None:
            # Extract the text from the salary element
            return salary_element.text.replace("\n", "").replace("\t", "").replace(" ","").strip()
    else:
        return None
    
#looking for $ amounts in the HTML String
def extract_salary_re(page):
    logging.debug(f"Trying to extract salary by regex")
    # page = get_job_description_page(url)
    
    if page is not None:

       # with open("job.txt", "a", encoding="utf-8") as file:
        #    file.write(page.prettify())  # Write the formatted HTML content to the file

        #print(f"Page content written")
        
        # Define a regex pattern to match salary amounts (e.g., $50,000 or $50000)
        # The pattern can be adjusted based on the expected format
        # This pattern matches dollar amounts with optional commas and decimals
        # The regex pattern is as follows:
        # \$ - Matches the dollar sign
        # \d{1,3} - Matches 1 to 3 digits
        # (?:,\d{3})* - Matches optional groups of 3 digits preceded by a comma
        # (?:\.\d{2})? - Matches optional decimal part with 2 digits
        # -?\d{1,3} - Matches optional negative sign and 1 to 3 digits
        # (?:,\d{3})* - Matches optional groups of 3 digits preceded by a comma
        # (?:\.\d{2})? - Matches optional decimal part with 2 digits
        # pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?'

        
        
        for reg in salary_regex:
            pattern = re.compile(reg, re.IGNORECASE)

            # Use the regex pattern to search for salary amounts in the text    
            # Search for the pattern in the text
            match = re.search(pattern,  page.find('div', {'class': 'description__text'}).text)
            
            if match is not None:
                logging.debug(f"Regex match: {match.group()}")
                # If a match is found, return it; otherwise, return None
                return match.group()
            
        return None
    else:
        return None


def extract_salary_re_first(description_page):
    salary = extract_salary_re(description_page)  # Placeholder for salary, if available
    if salary is None:
        logging.debug(f"Salary not found by regex")
        # Try to extract the salary using the current tag
        salary = extract_salary_by_tag_collection(description_page)
    if salary is None:
        debug_salary_extract(description_page)
        salary = "$0"
    logging.debug(f"\nExtracted {salary}")
    return salary

def extract_salary_tag_first(description_page):
    salary = extract_salary_by_tag_collection(description_page)  # Placeholder for salary, if available
    if salary is None:
        salary = extract_salary_re(description_page)
    if salary is None:
        debug_salary_extract(description_page)
        salary = "$0"
    logging.debug(f"\nExtracted {salary}")
    return salary

def extract_salary(soup):
    return extract_salary_re_first(soup)
    


######################################################
## Functions to get the job details off LinkedIn
#####################################################


def get_job_description_page(url):
    try:
        description_page = get_response(url)
        if description_page.status_code == 200:
            return BeautifulSoup(description_page.content, "html.parser")
        else:
            logging.debug(f"Failed to retrieve job description page. Status code: {description_page.status_code}")
            return None
    except requests.exceptions.ConnectionError as e:
        logging.debug(f"Connection error while fetching job description: {e}")
        return None
    
# Function to extract job description from the job URL found on LinkedIn
# Returns None if the job description is not found
def extract_job_description(job_description_soup):
#    print(f"Extracting job description from {job_url}")
   
   # job_description_soup = get_job_description_page(job_url)
    if job_description_soup is not None:
        job_description = job_description_soup.find('div', {'class': 'description__text'})

        if job_description is not None:
            job_description = job_description.text.strip()
            return job_description
        else:
            return None
    else:
        return None

# Function to extract job details from a job element (job card on LinkedIn)
# This function will extract the job title, company, location, date, URL, salary, and description
def extract_job_details(job_element):
    
    title = job_element.find('h3', {'class': 'base-search-card__title'}).text.strip()
    company = job_element.find('h4', {'class': 'base-search-card__subtitle'}).text.strip()
    location = job_element.find('span', {'class': 'job-search-card__location'}).text.strip()
    date = job_element.find('time')['datetime']
    url = job_element.find('a')['href']
    # Get the job description page
    description_page = get_job_description_page(url)
    description = extract_job_description(description_page)
    
    logging.debug(f"Job Title: {title}")
    # try to find the salary in different ways
    if description is not None:
        salary = extract_salary(description_page)
    else:
        logging.debug(f"Description not found for {title}")
        salary = "$0"  # Default value if description is not found

    return Job(title, company, location, date, url, salary, description)



    

# Extract job details from the LinkedIn page
# The soup object will be passed to this function
def extract_jobs(soup):
    logging.debug(">")
    job_elements = soup.find_all('div', {'class': job_string})
    
    jobs = []
    for job_element in job_elements:
        logging.debug(">")
        job = extract_job_details(job_element)
        jobs.append(job)
    
    return jobs




######################################################
## Functions to get the LinkedIn Search Results
#####################################################

def get_linkedin_page():
        # Check if the parameters were passed, and set the environment variables are set
    if parser.parse_args().username:
        os.environ["LINKEDIN_USERNAME"] = parser.parse_args().username
    if parser.parse_args().password:
        os.environ["LINKEDIN_PASSWORD"] = parser.parse_args().password
    if parser.parse_args().url:
        os.environ["LINKEDIN_URL"] = parser.parse_args().url
        print("Using URL from command line")
        print(f"LinkedIn URL: {os.getenv('LINKEDIN_URL')}")

    if not all([os.getenv("LINKEDIN_USERNAME"), os.getenv("LINKEDIN_PASSWORD"), os.getenv("LINKEDIN_URL")]):
        logging.error("Please set the LINKEDIN_USERNAME, LINKEDIN_PASSWORD, and LINKEDIN_URL environment variables")
        exit(0)
    # Get the credentials from environment variables``
    # Create an instance of the Credentials class
    credentials = Credentials(os.getenv("LINKEDIN_USERNAME"), os.getenv("LINKEDIN_PASSWORD"))

    session.auth = (credentials.username, credentials.password)
    # Make a GET request to the LinkedIn page using the session
    # Use the session to make the request
    search_page = get_response(os.getenv("LINKEDIN_URL"))
    if search_page.status_code == 429:
        raise requests.exceptions.RequestException("Rate limit exceeded")

    # Check if the request was successful (status code 200)
    if search_page.status_code != 200:
        logging.error("Failed to retrieve the page")
        exit(0)

    soup = BeautifulSoup(search_page.content, "html.parser")

    return soup



######################################################
## Functions to create output files
#####################################################

# Create a Tab Separated Values (TSV) file to store the job details    
def create_tsv_file(jobs):
    # Create a TSV file to store the job details
    with open(parser.parse_args().output, "w",) as file:
        # Write the header
        file.write("Title\tCompany\tLocation\tDate\tSalary\tURL\n")
        # Write the job details
        for job in jobs:
            file.write(f"{job.title}\t{job.company}\t{job.location}\t{job.date}\t{job.salary}\t{job.url}\n")

#######################################################################################################################    
### Main function to get the LinkedIn page and extract jobs
# This function will be called when the script is run
# It will return a list of jobs found on the LinkedIn page
def main():
    #setup commandline arguments
    setup_args()
    args = parser.parse_args()


    # Set up the HTTP session headers
    setup_session()
    
    # Get the LinkedIn page
    page = get_linkedin_page()
    logging.debug("Got the job search results")
    # Extract the jobs from the page
    jobs = extract_jobs(page)
    logging.debug("Extracted the jobs")
    return jobs



if __name__ == "__main__":
    
    logging.basicConfig(level=logging.ERROR)
    logging.debug("Starting LinkedIn Job Scraper")
    # dump_env()
    
    jobs = main()

    print(f"Jobs found: {len(jobs)} writing TSV file")
    # Create a TSV file to store the job details
    create_tsv_file(jobs)
    # Print the job details
    # print_jobs(jobs)
    # Print the job titles
    # print_job_titles(jobs)
