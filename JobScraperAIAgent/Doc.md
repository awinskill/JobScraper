# Agent Lifecycle

```mermaid
flowchart TD
    A[Environment State] --> B(Perceive)
    B --> C(Decide Plan)
    C --> D(Act - Real World)
    D --> E(Observe Outcome)
    E --> F(Critique & Learn)
    F --> B

    
## ✅ Perceive
- Open the job board URLs.
- Detect links (even hidden or behind JS — Selenium helps here).
- Use Trafilatura to auto-detect page content if structure varies.
- Use BeautifulSoup if the page structure is known.

## ✅ Decide
- Prioritize scraping:
* Newer postings first.
* Companies you haven't scraped before.
* Ignore duplicates (check against self.memory).

## ✅ Act
- Scrape page.
- Send text content to OpenAI to summarize and extract details:
* Title
* Company
* Location
* Salary
* Remote/onsite
* Save or output the structured data.

## ✅ Learn
- If scraping fails:
* Retry once.
* If structure changed, fallback to Trafilatura full-content extraction.

- Update memory:
* Add scraped job URL IDs to prevent duplication.
* Optionally, retrain rules based on what works better.