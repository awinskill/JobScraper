
from abc import ABC, abstractmethod
import logging
from job_scraper import Job
from job_scraper import GenAISummarizer


import json
import openai
import backoff
from openai import OpenAIError
import re

import trafilatura


DEV_MODE = True


class OpenAISummarizer(GenAISummarizer):

    def __init__(self, config, prompt_filename="prompt.txt"):
        """
        Initializes the OpenAISummarizer with the provided API key.
        
        Args:
            api_key (str): The API key for OpenAI.
        """
        self.__api_key = config["OpenAI"]["OPENAI_API_KEY"]
        self.__model = config["OpenAI"]["MODEL"]
        self.retry_on_no_salary = config["OpenAI"].getboolean("RETRY_ON_NO_SALARY", fallback=False)

        self._load_prompt(prompt_filename)

        logging.debug(f"OpenAI API key loaded successfully: {self.__api_key}")
        logging.debug(f"OpenAI model loaded successfully: {self.__model}")
        logging.debug(f"Prompt loaded successfully from {prompt_filename}")
       
        # Set up OpenAI API client here if needed
 
    def get_prompt(self):
        return self.__prompt
    
    def get_api_key(self):
        return self.__api_key
    
    def get_model(self):
        return self.__model
    
# read the prompt from the prompt file
    def _load_prompt(self, filename):
        """Load OpenAI Prompt"""
        # Open the file and read its contents
        self.__prompt = None

        with open(filename, "r", encoding="utf-8") as file:
            self.__prompt = file.read()

        file.close()
        logging.debug(f"Prompt loaded successfully from {filename}")
    






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
            salary_lower=_currency_to_int( parsed_summary.get("salary_lower", None)),
            salary_upper=_currency_to_int( parsed_summary.get("salary_upper", None)),
            description=parsed_summary.get("description", ""),
            summary=parsed_summary.get("summary", ""),
            fit=parsed_summary.get("fit", None),
            raw_description=raw_description)
    








    @backoff.on_exception(backoff.expo, (openai.OpenAIError, openai.APIError, openai.RateLimitError, openai.Timeout, BaseException), max_tries=20)
    def _query_openai(self, raw_description ):
        try:

            logging.debug(f"Input string: {super().get_prompt()}")

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




def _currency_to_int(currency: str) -> int:
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





class OpenAIStructuredSummarizer(OpenAISummarizer):

    def __init__(self, config, prompt_filename="prompt.txt"):
        OpenAISummarizer.__init__(self, config, prompt_filename)

        self.job_schema =  { 
            "format": {
                "name": "Job_Summarizer",
                "type": "json_schema",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                            "id": { "type": "integer" },
                            "title": { "type": "string" },
                            "company": { "type": "string" },
                            "location": { "type": "string" },
                            "date": { "type": "string" },
                            "url": { "type": "string" },
                            "salary": { "type": "string" },
                            "salary_lower": { "type": "integer" },
                            "salary_upper": { "type": "integer" },
                            "description": { "type": "string" },
                            "summary": { "type": "string" },
                            "fit": { "type": "integer" }
                        },
                
                    "required": [
                        "id",
                        "title",
                        "company",
                        "location",
                        "date",
                        "url",
                        "salary",
                        "salary_lower",
                        "salary_upper",
                        "description",
                        "summary",
                        "fit"
                    ],

                    "additionalProperties": False
                },
            }
        }


        

    def summarize(self, job: Job):

        # clean up the description using trafilatura
        # and then pass it to the OpenAI API
        # to get the summary. Reduce the number of tokens
        # by removing the HTML tags and other junk.
        logging.info("Cleaning up the description using trafilatura...")
        logging.info(f"Raw description size: {len(job.raw_description)}")
        

        # Use trafilatura to clean up the description
        clean_up_description = trafilatura.extract(job.raw_description)
        if clean_up_description is None:
            logging.error("Error cleaning up the description using trafilatura.")
            return None
        
        logging.info(f"Cleaned up description size: {len(clean_up_description)}")
        
        parsed_summary = self._openai_structured_query(clean_up_description)

        if parsed_summary is not None:
            # Create a Job object from the parsed JSON
            # OpenAI wont return the raw_description, so we need to add it manually
            # to the Job object. Don't want to incur the cost of those tokens!

            parsed_id = parsed_summary.get("id","Unkown ID")
            job_id = job.id if job.id is not None else parsed_id

            salary_upper = parsed_summary.get("salary_upper", None)

            if self.retry_on_no_salary:

                if salary_upper is None or salary_upper == 0:
                    # need to requery OPENAI with the   raw_description - so it has all the information 
                    logging.info("Requerying OpenAI with the raw description... EXPENSIVE!")
                    parsed_summary = self._openai_structured_query(job.raw_description)
                    if parsed_summary is None:
                        logging.error("Error requerying OpenAI with the raw description.")
                        return None

            return Job(
                id=job_id,
                source=job.source,
                title=parsed_summary.get("title", "Unknown Title"),
                company=parsed_summary.get("company", "Unknown Company"),
                location=parsed_summary.get("location", "Unknown Location"),
                date=parsed_summary.get("date", "Unknown Date"),
                url=job.url,
                salary=parsed_summary.get("salary", "Unknown Salary"),
                salary_lower=parsed_summary.get("salary_lower", None),
                salary_upper=parsed_summary.get("salary_upper", None),
                description=parsed_summary.get("description", ""),
                summary=parsed_summary.get("summary", ""),
                fit=parsed_summary.get("fit", None),
                raw_description=job.raw_description)


#    def summarize(self, source, url, raw_description):
#
#        parsed_summary = self._openai_structured_query(url=url, raw_description=raw_description)
#
#        if parsed_summary is not None:
            # Create a Job object from the parsed JSON
            # OpenAI wont return the raw_description, so we need to add it manually
            # to the Job object. Don't want to incur the cost of those tokens!
#            return Job(
#                id=parsed_summary.get("id","Unkown ID"),
#                source=source,
#                title=parsed_summary.get("title", "Unknown Title"),
#                company=parsed_summary.get("company", "Unknown Company"),
#                location=parsed_summary.get("location", "Unknown Location"),
#                date=parsed_summary.get("date", "Unknown Date"),
#                url=parsed_summary.get("url", "Unknown URL"),
#                salary=parsed_summary.get("salary", "Unknown Salary"),
#                salary_lower=parsed_summary.get("salary_lower", None),
#                salary_upper=parsed_summary.get("salary_upper", None),
#                description=parsed_summary.get("description", ""),
#                summary=parsed_summary.get("summary", ""),
#                fit=parsed_summary.get("fit", None),
#                raw_description=raw_description)

#        return None    


    @backoff.on_exception(backoff.expo, (openai.OpenAIError, openai.APIError, openai.RateLimitError, openai.Timeout, BaseException), max_time=600, max_tries=60, jitter=backoff.full_jitter)
    def _openai_structured_query(self, raw_description):
        try:

            

            logging.debug(f"Input string: {super().get_prompt()}")

            raw_input=""

 #           if url is None:
 #               raw_input = super().get_prompt() + str(raw_description)
 #           else:
 #               print("Using URL based prompt to reduce tokens, let the LLM go out on the web")
 #               raw_input = super().get_prompt() + str(url)

            raw_input = super().get_prompt() + str(raw_description)
 
            openai.api_key = super().get_api_key()

            prompt =  {"role": "user", "content": raw_input}

            response = openai.responses.create(
                model=super().get_model(),
                input=[
                    {"role": "system", "content": "You are a computer programmer & you will follow the instructions carefully."},
                    prompt                   
                    ],
                text=self.job_schema
                )
            
        except openai.OpenAIError as e:
            logging.error("Error querying OpenAI: %s",e)
            # logging.error(f"Model: {model} Temperature: {temp} Max Output Tokens: {max_tokens} Prompt: {prompt}")
            return None

        json_response = json.loads(response.output_text)
        return json_response       
    



