# models/job.py
class Job:
    """Job: Holds all the job information"""
    def __init__(self, linkedin_id, title, company, location, date, url=None, salary=None, salary_lower=None, salary_upper=None, description=None, summary=None, fit=None):
        self.linkedin_id = linkedin_id
        self.title = title
        self.company = company
        self.location = location
        self.date = date
        self.url = url
        self.salary = salary
        self.salary_lower = salary_lower
        self.salary_upper = salary_upper
        self.description = description
        self.summary = summary
        self.fit = fit

    def __str__(self):
        return f"ID: {self.linkedin_id}, Title: {self.title}, Company: {self.company}, Location: {self.location}, Date: {self.date}, URL: {self.url}, Salary: {self.salary}, Salary_Lower: {self.salary_lower}, Salary_Upper: {self.salary_upper}, Description: {self.description}, Summary: {self.summary}, Fit: {self.fit}"

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        return {
            "id": self.linkedin_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "date": self.date,
            "url": self.url,
            "salary": self.salary,
            "salary_lower": self.salary_lower,
            "salary_upper": self.salary_upper,
            "description": self.description,
            "summary": self.summary,
            "fit": self.fit
        }