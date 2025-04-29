import job_scraper
import configparser
import logging
import backoff

from job_scraper import Job
from job_scraper import GenAISummarizer
import json

import openai   #deepseek uses the OpenAI API
from openai import OpenAI


class DeepseekSummarizer(GenAISummarizer):

    def __init__(self, config, prompt_filename="prompt.txt"):
        """
        Initializes the OpenAISummarizer with the provided API key.
        
        Args:
            api_key (str): The API key for OpenAI.
        """
        logging.info("Initializing DeepseekSummarizer...")

        self.__api_key = config["Deepseek"]["DEEPSEEK_API_KEY"]
        self.__model = config["Deepseek"]["MODEL"]

        self._load_prompt(prompt_filename)

        logging.debug(f"Deepseek API key loaded successfully: {self.__api_key}")
        logging.debug(f"Deepseek model loaded successfully: {self.__model}")
        logging.debug(f"Prompt loaded successfully from {prompt_filename}")
       
        # Set up OpenAI API client here if needed
        self.client = OpenAI(
            api_key=self.__api_key,
            base_url="https://api.deepseek.com",
        )
 
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
        logging.debug("Summarizing text using Deepseek API...")
    
        summary = self._query_deekseek( str(raw_description))
        if summary is None:
            logging.error("Failed to summarize text using OpenAI API.")
            return None

        logging.debug("Received summary from OpenAI API.")
        logging.debug(f"Summary: {summary}")
        
        parsed_summary = None

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
        salary_lower = parsed_summary.get("salary_lower", None)
        salary_upper = parsed_summary.get("salary_upper", None)

        return Job(
            id=parsed_summary.get("id","Unkown ID"),
            title=parsed_summary.get("title", "Unknown Title"),
            company=parsed_summary.get("company", "Unknown Company"),
            location=parsed_summary.get("location", "Unknown Location"),
            date=parsed_summary.get("date", "Unknown Date"),
            url=parsed_summary.get("url", "Unknown URL"),
            salary=parsed_summary.get("salary", "Unknown Salary"),
            salary_lower= salary_lower,
            salary_upper= salary_upper,
            description=parsed_summary.get("description", ""),
            summary=parsed_summary.get("summary", ""),
            fit=parsed_summary.get("fit", None),
            raw_description=raw_description)
    

    @backoff.on_exception(backoff.expo, (openai.OpenAIError, openai.APIError, openai.RateLimitError, openai.Timeout, BaseException), max_tries=20)
    def _query_deekseek(self, raw_description ):
        try:

            logging.debug(f"Input string: {self.get_prompt()}")

            raw_input = self.__prompt + raw_description


            messages = [
            {"role": "user", "content": raw_input}]

            response = self.client.chat.completions.create(
                model=self.get_model(),
                messages=messages,
                temperature=0.1,  # Adjust for creativity (0.0 = deterministic, 1.0 = more creative)
                response_format={
                    'type': 'json_object'
                }
            )

            json_response = str(response.choices[0].message.content)

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