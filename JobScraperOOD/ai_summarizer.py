
from abc import ABC, abstractmethod
import logging
from job_scraper import Job
from job_scraper import GenAISummarizer


import json
import openai
import backoff
from openai import OpenAIError
import re




class OpenAISummarizer(GenAISummarizer):

    def __init__(self, config, prompt_filename="prompt.txt"):
        """
        Initializes the OpenAISummarizer with the provided API key.
        
        Args:
            api_key (str): The API key for OpenAI.
        """
        self.__api_key = config["OpenAI"]["OPENAI_API_KEY"]
        self.__model = config["OpenAI"]["MODEL"]

        self._load_prompt(prompt_filename)

        logging.debug(f"OpenAI API key loaded successfully: {self.__api_key}")
        logging.debug(f"OpenAI model loaded successfully: {self.__model}")
        logging.debug(f"Prompt loaded successfully from {prompt_filename}")
       
        # Set up OpenAI API client here if needed

# read the prompt from the prompt file
    def _load_prompt(self, filename):
        """Load OpenAI Prompt"""
        # Open the file and read its contents
        self.__prompt = None

        with open(filename, "r", encoding="utf-8") as file:
            self.__prompt = file.read()

    






    def summarize(self, raw_description: str) -> Job:
        """
        Summarizes the given text using OpenAI's API. The text should be the raw job description from the job board.
        This method will call the OpenAI API to summarize the text and return a Job object with the summarized description.
        
        This is the implementation of the abstract method from the JobSummarizer class.
        
        The GenAI needs to return a JSON structure which will be used to create the Job object.
        The JSON structure should contain the following fields:
            - title
            - company
            - location
            - date
            - url
            - salary
            - salary_lower
            - salary_upper
            - description
            - summary
            - fit
            - raw_description (the original raw text of the HTML web page including the tags)


        Args:
            text (str): The text to summarize.
        
        Returns:
            Job: An object created by the information returned from the GenAI.
        """
        logging.debug("Summarizing text using OpenAI API...")
    
        summary = self._query_openai( str(raw_description))
        if summary is None:
            logging.error("Failed to summarize text using OpenAI API.")
            return None

        logging.debug("Received summary from OpenAI API.")
        logging.debug(f"Summary: {summary}")
        
        try:
            # Parse the JSON summary
            parsed_summary = json.loads(summary)
            logging.debug(f"Parsed JSON = {parsed_summary}")
                          
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON from OpenAI response: {e}")
            return None

        

        # Create a Job object from the parsed JSON
        # OpenAI wont return the raw_description, so we need to add it manually
        # to the Job object. Don't want to incur the cost of those tokens!
        return Job(
            id=parsed_summary.get("linkedin_id","Unkown ID"),
            title=parsed_summary.get("title", "Unknown Title"),
            company=parsed_summary.get("company", "Unknown Company"),
            location=parsed_summary.get("location", "Unknown Location"),
            date=parsed_summary.get("date", "Unknown Date"),
            url=parsed_summary.get("url", "Unknown URL"),
            salary=parsed_summary.get("salary", "Unknown Salary"),
            salary_lower=currency_to_int( parsed_summary.get("salary_lower", None)),
            salary_upper=currency_to_int( parsed_summary.get("salary_upper", None)),
            description=parsed_summary.get("description", ""),
            summary=parsed_summary.get("summary", ""),
            fit=parsed_summary.get("fit", None),
            raw_description=raw_description)
    








    @backoff.on_exception(backoff.expo, (openai.OpenAIError, openai.APIError, openai.RateLimitError, openai.Timeout, BaseException), max_tries=20)
    def _query_openai(self, raw_description ):
        try:

            logging.debug(f"Input string: {self.__prompt}")

            raw_input = self.__prompt + raw_description


            openai.api_key = self.__api_key
            response = openai.responses.create(
                model=self.__model,\
                instructions="You are a computer programmer & you will follow the instructions carefully.",
                input= raw_input,
                temperature=0.1,  # Adjust for creativity (0.0 = deterministic, 1.0 = more creative)
                max_output_tokens=500   # Adjust for response length
            )

            json_response = str(response.output_text)

            json_response = json_response.replace("`", "").replace("\n", "")

            #check there is no text before the opening {
            json_response = "{" + json_response.split("{", 1)[1]

            return json_response
        
        except openai.OpenAIError as e:
            logging.error("Error querying OpenAI: %s",e)
            # logging.error(f"Model: {model} Temperature: {temp} Max Output Tokens: {max_tokens} Prompt: {prompt}")
            return None




def currency_to_int(currency: str) -> int:
    """
    Converts a currency string to an integer.
    
    Args:
        currency (str): The currency string (e.g., "$120,000", "£85,000").
    
    Returns:
        int: The numeric value of the currency.
    """
    if not currency:
        return 0  # Return 0 if the input is None or empty
    
    # Remove non-numeric characters (except for the decimal point)
    cleaned_currency = re.sub(r"[^\d.]", "", currency)
    
    # Convert to integer (rounding if necessary)
    return int(float(cleaned_currency))

if __name__ == "__main__":
    
    print("No test code provided for OpenAI Summarizer.")