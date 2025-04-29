
from abc import ABC, abstractmethod
import logging
import backoff
from job_scraper import Job
from job_scraper import GenAISummarizer


import json
import anthropic


class AnthropicSummarizer(GenAISummarizer):
    def __init__(self, configParser, prompt_file):
        self.__api_key = configParser["Anthropic"]["ANTHROPIC_API_KEY"]
        self.__model = configParser["Anthropic"]["ANTHROPIC_MODEL"]

        

        logging.debug(f"OpenAI API key loaded successfully: {self.__api_key}")
        logging.debug(f"OpenAI model loaded successfully: {self.__model}")
        logging.debug(f"Prompt loaded successfully from {prompt_file}")
        
        self.config = configParser
    
        # Open the prompt file and read its contents
        self.__prompt = None

        with open(prompt_file, "r", encoding="utf-8") as file:
            self.__prompt = file.read()

        logging.debug(f"Prompt loaded successfully from {prompt_file}")
        file.close()
    
    
 
    def get_prompt(self):
        return self.__prompt
    
    def get_api_key(self):
        return self.__api_key
    
    def get_model(self):
        return self.__model
    
    def summarize(self, raw_description: str) -> Job:
        
        """Summarizes the given text using the Anthropic API.
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
        logging.debug("Summarizing text using Anthropic API...")
    
        summary = self._query_anthropic( str(raw_description))
        if summary is None:
            logging.error("Failed to summarize text using Anthropic API.")
            return None

        logging.debug("Received summary from Anthropic API.")
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
            id=parsed_summary.get("id","Unkown ID"),
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
    


    @backoff.on_exception(backoff.expo, (anthropic.AnthropicError, anthropic.APIConnectionError, BaseException), max_tries=20)
    def _query_anthropic(self, raw_description ):
        try:

            logging.debug(f"Querying Anthropic with model {self.__model}")

            raw_input = self.__prompt + raw_description

            client = anthropic.Anthropic(
                api_key=self.get_api_key()
            )

            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": raw_input}
                ]
            )

               # Debug the response structure
            logging.debug(f"Anthropic response: {message}")

            # Extract the content from the response
            if hasattr(message, "content") and isinstance(message.content, list):
                # Extract the first TextBlock and its text
                text_block = message.content[0]
                if hasattr(text_block, "text"):
                    json_response = text_block.text
                else:
                    logging.error("TextBlock does not contain 'text' attribute.")
                    return None
            else:
                logging.error("Message content is not in the expected format.")
                return None


            json_response = json_response.replace("`", "").replace("\n", "")

            #check there is no text before the opening {
            json_response = "{" + json_response.split("{", 1)[1]

            return json_response
        
        except anthropic.AnthropicError as e:
            logging.error("Error querying Anthropic: %s",e)
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