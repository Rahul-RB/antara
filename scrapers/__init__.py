from scrapers.an_scraper import AnuragaScraper
from scrapers.as_scraper import AseemaScraper
from scrapers.base import BaseScraper


def get_scraper(site: str) -> BaseScraper:
    if site == "as":
        return AseemaScraper()
    if site == "an":
        return AnuragaScraper()
    raise ValueError(f"Unknown site: {site}")
