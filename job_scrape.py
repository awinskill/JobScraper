#######################################
## job_scrape.py - LinkedIn Job Scraper
#######################################
# pylint: disable=invalid-name
# pylint: disable=line-too-long
# pylint: disable=trailing-whitespace
# pylint: disable=missing-function-docstring
# pylint: disable=missing-module-docstring
# pylint: disable=trailing-newlines


import sys
import logging
import json

import configparser
from argparse import ArgumentParser


import openai
import requests
import backoff
import pyodbc
# import pymssql
import os

from job import Job


from bs4 import BeautifulSoup
from openai import OpenAIError




# Global configuration
config = configparser.RawConfigParser()

# Default HTTP settings for get_response
http_max_tries = 8
http_max_time=60

# Default for OpenAI decorator
openai_max_tries=8

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


username = None
password = None
linkedin_url = None






        





@backoff.on_exception(
    backoff.expo,  # Exponential backoff
    pyodbc.Error,  # Retry on pyodbc errors
    max_tries=5,   # Maximum number of retries
    jitter=None    # Optional: Add randomness to backoff intervals
)
def get_conn(connection_string):
    try:
        connection = pyodbc.connect(connection_string)

        if connection is None:
            logging.error("Unable to connect to Azure SQL")
            return None
        logging.debug("Connected to Azure SQL")
        return connection
    except pyodbc.Error as e:
        logging.error("Error connecting to Azure SQL: %s", e)
        return None
    except Exception as e:
        logging.error("Error connecting to Azure SQL: %s", e)
        return None

def get_cursor(connection):
    cursor = connection.cursor()

    if cursor is None:
        logging.error("Unable to get cursor")
        return None
    logging.debug("Got cursor")
    return cursor

def add_job_to_db(connection_string, job):
    connection = get_conn(connection_string)

    if connection is None:
        logging.error("Unable to connect to Azure SQL")
        return False
    
    cursor = get_cursor(connection)

    if cursor is None:
        logging.error("Unable to get cursor")
        return False

    # Insert the job into the database
    try:
        cursor.execute(
            'INSERT INTO LinkedInJobs (id, title, company, location, date, url, salary_lower, salary_upper, description, summary, salary, fit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (convert_to_int(job.linkedin_id), job.title, job.company, job.location, job.date, job.url, convert_to_int(job.salary_lower), convert_to_int(job.salary_upper), job.description, job.summary, job.salary, convert_to_int(job.fit))
        )
    except pyodbc.IntegrityError as e:
        # this is a common error when the job already exists in the database
        # log this as Info, not an error & return true as the job is already in the database
        logging.info("Job already exists in database. Skipping")
        return True
    except pyodbc.Error as e:
        logging.error("Error inserting job into database: %s", e)
        return False

    # Commit the changes
    connection.commit()

    logging.debug("Job added to database")
    return True

#################################################
## UTILITY FUNCTIONS
#################################################
# setup command line arguments
def setup_args():
    parser.add_argument("-u", "--username", help="LinkedIn username", required=False)
    parser.add_argument("-p", "--password", help="LinkedIn password", required=False)
    parser.add_argument("-l", "--url", help="LinkedIn URL", required=False)
    parser.add_argument("-o", "--output", help="Output file name", required=False, default="jobs.tsv")
    parser.add_argument("-i", "--info", help="Show info", required=False, default=False, action="store_true")
    parser.add_argument("-rr","--resetresumes", help="Reset the resume files", required=False, default=False, action="store_true")
    parser.parse_args()


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

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=http_max_tries, max_time=http_max_time, logger=logging)
def get_response(url):
    response = session.get(url)
    if response.status_code == 429:
        raise requests.exceptions.RequestException("Rate limit exceeded")

    if response.status_code == 200:
        logging.debug("HTTP Response: returning valid response")
        return response
    
    logging.error("Failed with status code: %s", response.status_code)
    return None
    




######################################################
## Functions to get the job details off LinkedIn
#####################################################


def get_job_description_page(url):
    try:
        description_page = get_response(url)
        if description_page.status_code == 200:
            return description_page.text
  
    except requests.exceptions.ConnectionError as e:
        logging.error("Connection error while fetching job description: %s", e)        
    except requests.exceptions.RequestException as e:
        logging.error("Error accessing page %s", e)

    logging.error("Failed to retrieve job description page. Status code: %s",description_page.status_code)   
    return None

# Function to extract job details from a job element (job card on LinkedIn)
# This function will extract the job title, company, location, date, URL, salary, and description
def extract_job_details(job_element):
    
    url = job_element.find('a')['href']
    # Get the job description page
    if url is not None:
        return get_job_description_page(url)
    
    return None
    

    

# Extract job details from the LinkedIn page
# The soup object will be passed to this function
def extract_jobs(soup):
    logging.debug(">")
    # job_string = "scaffold-layout__list "
    logging.debug(f"Extracting jobs with {job_string}")
    job_elements = soup.find_all('div', {'class': job_string})
    
    jobs = []
    for job_element in job_elements:
        logging.debug(">")
        job = extract_job_details(job_element)
        jobs.append(job)
    
    logging.info(f"Found {len(jobs)} jobs")
    return jobs




######################################################
## Functions to get the LinkedIn Search Results
#####################################################

def get_linkedin_search_page():
    # pylint: disable=global-statement
    """ Uses global variables and will generate a pylint warning """

    global linkedin_url
    global password
    global username

        # Check if the parameters were passed, and set the access variables
    if parser.parse_args().username:
        username = parser.parse_args().username
    else:
        username = config["LinkedIn"]["LINKEDIN_USERNAME"]
                                      
    if parser.parse_args().password:
        password = parser.parse_args().password
    else:
        password = config["LinkedIn"]["LINKEDIN_PASSWORD"]

    if parser.parse_args().url:
        linkedin_url = parser.parse_args().url
    else:
        linkedin_url = config["LinkedIn"]["LINKEDIN_URL"]

        if linkedin_url is not None:
            linkedin_url = linkedin_url.replace("\"","")
        else:
            logging.error("Unable to load LINKEDIN_URL")
            return None

   
    logging.info(f"Search URL {linkedin_url}")

    session.auth = (username, password)
    # Make a GET request to the LinkedIn page using the session
    # Use the session to make the request
    search_page = get_response(linkedin_url)
    if search_page.status_code == 429:
        raise requests.exceptions.RequestException("Rate limit exceeded")

    # Check if the request was successful (status code 200)
    if search_page.status_code != 200:
        logging.error("Failed to retrieve the page")
        sys.exit(0)

    soup = BeautifulSoup(search_page.content, "html.parser")

    logging.debug("Got the LinkedIn page")
    return soup



######################################################
## Functions to create output files
#####################################################

# Create a Tab Separated Values (TSV) file to store the job details    
def create_tsv_file(jobs):
    # Create a TSV file to store the job details
    with open(parser.parse_args().output, "w", encoding="utf-8")  as file:
        # Write the header
        file.write("ID\tTitle\tCompany\tLocation\tDate\tSalary\tSalary_Lower\tSalary_Upper\tSummary\tDescription\tURL\tFit\n")

        # Write the job details
        for job in jobs:
            file.write(f"{job.linkedin_id}\t{job.title}\t{job.company}\t{job.location}\t{job.date}\t{job.salary}\t{job.salary_lower}\t{job.salary_upper}\t{job.summary}\t{job.description}\t{job.url}\t{job.fit}\n")


# Create a Tab Separated Values (TSV) file to store the job details    
def upload_to_db(connection_string, jobs):
 
    for job in jobs:
        # Add the job to the database
        add_job_to_db(connection_string, job)



### Open AI things
def reset_openai_files():
    # Reset the OpenAI files
    try:
        setup_openai_key()
        filelist = openai.files.list()
        for file in filelist.data:
            if file.purpose == "user_data":
                openai.files.delete(file.id)
                logging.info(f"Deleted file {file.id} from OpenAI")
    except openai.OpenAIError as e:
        logging.error(f"Error deleting OpenAI files: %s", e)
        return None
    
    except Exception as e:
        logging.error(f"General Error deleting OpenAI files: %s", e)
        return None
    
    return True
## Get list of resume
def get_resume_files():
    # Get the list of resume files
    resume_files = []
    resume_dir = config["Resume"]["RESUME_DIR"]
    for file in os.listdir( resume_dir ):
        if file.endswith(".pdf"):
            filename = os.path.join(resume_dir, file)
            resume_files.append(filename)
            logging.info(f"Found resume file: {filename}")
    
    return resume_files


def make_input_string(prompt, fileids):

    # Add files
    input='[ {"role": "user", "content": ['
    for file in fileids:
        input += f' {{ "type": "input_file", "file_id": {file}, }},'
    input+= "]"

    # Add prompt
    input += f', {{"type": "input_text", "text": {prompt} }} ]'    

    return input


@backoff.on_exception(backoff.expo, OpenAIError, max_tries=openai_max_tries)
def upload_resume_files():
    try:
        fileids = []

        for filename in get_resume_files():
                # Upload the file to OpenAI
                file = openai.files.create(
                    file=open(filename, "rb"),
                    purpose="user_data" 
                )
                logging.info(f"Uploaded {file} to OpenAI")
                
                fileids.append(file.id)

        return fileids
    
    except openai.OpenAIError as e:
        logging.error(f"Error uploading resume files: %s", e)
        return None




@backoff.on_exception(backoff.expo, OpenAIError, max_tries=openai_max_tries)
def query_openai(prompt, model="gpt-3.5-turbo", temp=0.1, max_tokens=500):
    try:

        # Check if the files are already uploaded
        filelist = openai.files.list()
        fileids = []

        if not any(filelist):
            logging.error("No files found in OpenAI")
            fileids = upload_resume_files()

        input_string = make_input_string(prompt, filelist)

        logging.debug(f"Input string: {input_string}")

        response = openai.responses.create(
            model=model,
            instructions="You are a computer programmer & you will follow the instructions carefully.",
            input= input_string,
            temperature=temp,  # Adjust for creativity (0.0 = deterministic, 1.0 = more creative)
            max_output_tokens=max_tokens    # Adjust for response length
        )
        return response.output_text
    except openai.OpenAIError as e:
        logging.error("Error querying OpenAI: %s",e)
        # logging.error(f"Model: {model} Temperature: {temp} Max Output Tokens: {max_tokens} Prompt: {prompt}")
        return None

# read the prompt from the prompt file
def load_prompt(filename):
    """Load OpenAI Prompt"""
    # Open the file and read its contents
    contents = None

    with open(filename, "r", encoding="utf-8") as file:
        contents = file.read()

    return contents
 
def setup_openai_key():
    try:
        openai.api_key = config["OpenAI"]["OPENAI_API_KEY"]
    except KeyError:
        logging.error("OpenAI API key not found in config file")
        return None
    except Exception as e:
        logging.error("Error setting up OpenAI API key: %s", e)
        return None
    return True



def get_job_json_via_genai(job):
    # pylint: disable=global-statement

    prompt = None
    model = None
   

    prompt = load_prompt(config["OpenAI"]["LINKEDIN_PROMPT_FILE"])
    # add the HTML job page to the prompt
    prompt = prompt + ". Here is the job description: " + job

    # Set up the OpenAI API key
    setup_openai_key()
     
    model = config["OpenAI"]["MODEL"]
    temp = float(config["OpenAI"]["TEMPERATURE"])
    max_tokens = int(config["OpenAI"]["MAX_TOKENS"])
    
    global openai_max_tries
    openai_max_tries=int(config["OpenAI"]["OPENAI_MAX_RETRIES"])

    logging.debug("Using model %s", model)


    response = query_openai(prompt, model, temp=temp, max_tokens=max_tokens)

    logging.debug(response)
    #clean up the response and return
    if response is not None:
        return response.replace("`","").replace("json","").replace("\t"," ").replace("\n"," ").replace("\r"," ")
    
    return None

# convert via genAI
def convert_via_genai(raw_jobs):
    # for each raw page, go to genAI and get the JSON object filled
    jobs = []

    for job in raw_jobs:
        jobs.append(get_job_json_via_genai(job))

    return jobs

#check the JSON string can be processed
def is_valid_json(json_string):

    if (json_string is None) or (len(json_string) == 0):
        logging.error("Empty JSON string")
        return False
    
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError as e:
        logging.error("Invalid json %s", e)
        return False

def convert_jobs_json(jobs_json):
    # `jobs_json` is a list of JSON strings, so iterate over it
    jobs = []
    for job_json in jobs_json:
        if not is_valid_json(job_json):
            logging.error("Invalid json skipping")
            continue

        # Parse each JSON string into a dictionary
        job_dict = json.loads(job_json)
        
        # Convert the dictionary into a Job object
        # checking there are no tab characters in the JSON
        job = Job(
            linkedin_id=job_dict.get("linkedin_id"),
            title=job_dict.get("title"),
            company=job_dict.get("company"),
            location=job_dict.get("location"),
            date=job_dict.get("date"),
            url=job_dict.get("url"),
            salary=job_dict.get("salary"),
            salary_lower=job_dict.get("salary_lower"),
            salary_upper=job_dict.get("salary_upper"),
            description=job_dict.get("description"),
            summary=job_dict.get("summary"),
            fit=job_dict.get("fit")
        )
        jobs.append(job)
    
    return jobs



#######################################################################################################################    
### Main function to get the LinkedIn page and extract jobs
# This function will be called when the script is run
# It will return a list of jobs found on the LinkedIn page
# Outline structure:
#   1. Process the LinkedIn search page and build a list of jobs. Use screen scraping to get the list
#   2. Get the LinkedIn content for the job - otherwise we are dependant on the GenAI being able to go out onto the web
#   3. Use GenAI to build up a JSON structure in a single prompt, give the AI the JSON structure and the job description web content
#   4. Write the list of JSON objects into a TSV file for processing in Excel

def main():
    # pylint: disable=global-statement
    

    # load up the configuration
    config.read("config.ini")


    global http_max_tries
    global http_max_time

    http_max_tries= config["HTTP"]["MAX_RETRIES"]
    http_max_time = config["HTTP"]["MAX_TIME"]

    #setup commandline arguments
    setup_args()
   
    if parser.parse_args().info:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)
    
    logging.debug("Starting LinkedIn Job Scraper")
    # dump_env()

    if parser.parse_args().resetresumes:
        logging.info("Resetting OpenAI files")
        reset_openai_files()


    # Set up the HTTP session headers
    setup_session()
    # Get the LinkedIn page
    logging.info("Going to LinkedIn")
    page = get_linkedin_search_page()
    logging.debug("Got the job search results")

    # Extract the jobs from the page
    # should return an array of raw HTML
    logging.info("Scraping the jobs")
    job_raw_contents = extract_jobs(page)
    logging.debug("Extracted the jobs")

    # Get the JSON
    logging.info("Going to GenAI")
    jobs_json = convert_via_genai(job_raw_contents)

    # Turn the JSON into objects
    jobs = convert_jobs_json(jobs_json)

    # Create a TSV file to store the job details

    #print(f"Jobs found: {len(jobs)} writing TSV file")
    create_tsv_file(jobs)
    
    logging.info("Uploading to DB")
    upload_to_db(config["Azure"]["AZURE_SQL_CONNECTIONSTRING"].replace("\"",""), jobs)
    logging.info("Done")
    return jobs_json




if __name__ == "__main__":
  
    joblist = main()

