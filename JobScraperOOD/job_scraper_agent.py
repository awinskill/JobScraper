import job_scraper
import configparser

class JobScraperAgent:
    def __init__(self, config:configparser.RawConfigParser):
        self.config = config   # configuration for the job sources
        self.memory = {}         # Track what we've already scraped
        self.plan = []            # List of actions to take
        self.browser = None
    

    def perceive(self):
        # Fetch new job pages
        pass

    def decide(self):
        # Decide which pages to prioritize (e.g., newest postings)
        pass

    def act(self):
        # Scrape, summarize, and extract
        pass

    def learn(self):
        # Adapt to failures or changes in page structures
        pass

    def run(self):
        while not self.goal_reached():
            self.perceive()
            self.decide()
            self.act()
            self.learn()