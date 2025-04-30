import logging
import configparser
import urllib.parse
import openai
import json
import re


def build_linkedin_job_search_url(plan: dict) -> str:
    """
    Build a LinkedIn job search URL from a search plan.
    
    Args:
        plan (dict): Dictionary containing search parameters.

    Returns:
        str: LinkedIn job search URL.
    """
    base_url = plan.get("base_url", "https://www.linkedin.com/jobs/search/")
    location = plan.get("location", "Seattle, WA")
    distance = plan.get("distance", "25")
    keywords = plan.get("keywords", [])
    published_time = plan.get("published_time", "60")  # in days

    # Join keywords with spaces and URL-encode
    keyword_query = urllib.parse.quote(" ".join(keywords))
    # Encode location
    location_query = urllib.parse.quote(location)

    time_filter = int(published_time) * 60

    # Build query string
    query_params = f"keywords={keyword_query}&location={location_query}&distance={distance}&f_TPR=r{time_filter}"
    full_url = f"{base_url}?{query_params}"

    return full_url




class JobScraperAgent:
    def __init__(self, config: configparser.RawConfigParser, goal: str, logger=None):
    
        self.logger = logger
        if logger is None:
            logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
            self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing JobScraperAgent...")


        self.config = config   # configuration for the job sources
        self.memory = {}         # Track what we've already scraped
        self.browser = None
        self.goal = goal
        self.goal_reached = False

        self.plan = {
            "source" : "LinkedIn",
            "base_url": self.config["LinkedIn"].get("LINKEDIN_BASE_URL"),
            "criteria": {
                "location": "Seattle, WA",
                "published_time": self.config["LinkedIn"].get("LINKEDIN_TIME_FILTER", "60"),
                "distance": "25",
                "keywords": ["Leader", "AI"]
            },
            "steps": [
                "Create LinkedIn URL",
                "Navigate to LinkedIn jobs search page",
                "Scrape the list of job postings",
                "Extract job titles, companies, locations, and timestamps",
                "Summarize job details",
                "Store or return structured job data"
            ],
            "completion_criteria": {
               "stop_when": "all jobs within past hour found",
                "max_jobs": 50
            }
        }            


        self.plan['steps'] = [
            {"name": "create_url", "priority": 1},
            {"name": "get_search_page", "depends_on": "create_url"},
            {"name": "scrape_jobs", "depends_on": "get_search_page"},
            {"name": "summarize_jobs", "depends_on": "scrape_jobs"},
            {"name": "store_results", "depends_on": "summarize_jobs"}
        ]

        self.state = {
            "url_created": False,
            "search_page_loaded": False,
            "job_list_scraped": False,
            "jobs_summarized": False,
            "results_stored": False
        }

        
 

    def _parse_goals(self):
        return self.plan

    def perceive(self):
        logging.info("Perceiving the environment...")
        logging.debug(f"Current goal: {self.goal}")
        # Identify plan
        self.plan = self._parse_goals_with_openai()
        self.plan['steps'] = [
            {"name": "create_url", "priority": 1},
            {"name": "get_search_page", "depends_on": "create_url"},
            {"name": "scrape_jobs", "depends_on": "get_search_page"},
            {"name": "summarize_jobs", "depends_on": "scrape_jobs"},
            {"name": "store_results", "depends_on": "summarize_jobs"}
        ]
        logging.debug(f"Perceived plan: {self.plan}")
        pass

    def decide(self):
        # Decide which pages to prioritize (e.g., newest postings)
        pass

    def act(self, action):
        # Scrape, summarize, and extract
        pass

    def learn(self):
        # Adapt to failures or changes in page structures

        self.goal_reached = True
        pass




    def run(self):
        while not self.goal_reached:
            self.perceive()
            self.decide()
           

            while True:
                action = self.decide_next_action()
                if not action:
                    print("[Agent] Goal completed!")
                    break
                print(f"[Agent] Deciding to: {action}")
                self.act(action)

            self.learn()



    def _parse_goals_with_openai(self):
        self.logger.info("Calling OpenAI to parse goal into a plan...")
        
        openai.api_key = self.config["OpenAI"]["OPENAI_API_KEY"]

        client = openai.Client(
            api_key=openai.api_key
        )
        self.logger.info("OpenAI client initialized.")
        prompt = f"""
    You are a job search planner. The user’s goal is:

    \"{self.goal}\"

    Return a JSON object using the following structure:
    {{
        "source": "LinkedIn",
        "base_url": "https://www.linkedin.com/jobs/search/",
        "criteria": {{
            "location": "<city, state or region>",
            "published_time": "<time in minutes>",
            "distance": "<radius in miles>",
            "keywords": ["<list>", "<of>", "<keywords>"]
        }},
        "steps": [
            "Create LinkedIn URL",
            "Navigate to LinkedIn jobs search page",
            "Scrape the list of job postings",
            "Extract job titles, companies, locations, and timestamps",
            "Summarize job details",
            "Store or return structured job data"
        ],
        "completion_criteria": {{
            "stop_when": "all jobs within past hour found",
            "max_jobs": 50
        }}
    }}

    Be concise. Only return the JSON.
    """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You convert goals into executable search plans for LinkedIn job scraping."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )

            raw_content = response.choices[0].message.content

            # Strip Markdown formatting (if any)
            cleaned_content = re.sub(r"```(?:json)?\n?", "", raw_content)
            cleaned_content = cleaned_content.replace("```", "").strip()


            plan = json.loads(cleaned_content)
            return plan

        except Exception as e:
            self.logger.error(f"OpenAI call failed: {e}")
            self.logger.warning("Falling back to default plan.")
            return self.default_plan

 

    def decide_next_action(self):
        if not self.state["url_created"]:
            return "create_url"
        elif not self.state["search_page_loaded"]:
            return "get_search_page"
        elif not self.state["job_list_scraped"]:
            return "scrape_jobs"
        elif not self.state["jobs_summarized"]:
            return "summarize_jobs"
        elif not self.state["results_stored"]:
            return "store_results"
        else:
            return None
        

    def act(self, action):
        if action == "create_url":
            self.logger.info("Creating LinkedIn job search URL...")    
            self.state["url_created"] = True

        elif action == "get_search_page":
            self.logger.info("Getting search page...")    
            self.state["search_page_loaded"] = True

        elif action == "scrape_jobs":
            self.logger.info("Scraping job list...")
            self.state["job_list_scraped"] = True

        elif action == "summarize_jobs":
            self.logger.info("Summarizing job details...")
            self.state["jobs_summarized"] = True

        elif action == "store_results":
            self.logger.info("Storing results...")
            self.state["results_stored"] = True

        else:
            print(f"[Agent] Unknown action: {action}")
            
if __name__ == "__main__":
  
    # Load configuration
    config = configparser.RawConfigParser()
    config.read("config.ini")  # Ensure you have a `config.ini` file with LinkedIn credentials and URL

    # Check if the configuration file is loaded
    if not config.sections():
        print("Failed to load configuration file.")
        sys.exit(1)

    goal = config["LinkedIn"].get("LINKEDIN_GOAL", "Find AI-related jobs in Seattle")

    # Initialize JobScraperAgent
    agent = JobScraperAgent(config, goal)

    
    agent.run()