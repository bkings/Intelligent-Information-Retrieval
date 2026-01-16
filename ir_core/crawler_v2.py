import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict

BASE_URL = "https://pureportal.coventry.ac.uk"
ORG_URL = (
    BASE_URL
    + "/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo"
)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (compatible; CoventryIRBot/1.0; " "Academic use only)")
}

CRAWL_DELAY = 2  # politeness delay in seconds


def fetch_page(url: str) -> BeautifulSoup:
    time.sleep(CRAWL_DELAY)
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_publications_page_url() -> str:
    soup = fetch_page(ORG_URL)
    subMenu = soup.select_one("#page-content .subMenu")

    if not subMenu:
        raise RuntimeError("Sub Menu not found on organization page")

    for link in subMenu.find_all("a", href=True):
        href = link["href"]
        print(f"HREF from menu: {href}")
        if "publications" in href:
            return urljoin(BASE_URL, href)

    raise RuntimeError("Publications link not found")


def crawl_publication_list(publication_url: str) -> List[str]:
    soup = fetch_page(publication_url)

    results = soup.select("#page-content .list-results a[href]")
    publication_urls = set()

    for a in results:
        href = a["href"]
        print(f"Publication url: {href}")
        if "/publications" in href:
            publication_urls.add(urljoin(BASE_URL, href))

    return list(publication_urls)


def crawl_individual_publication(url: str) -> Dict:
    """
    Extracts structured metadata from the page
    """
    soup = fetch_page(url)
    title = soup.find("h1")
    year = soup.find("span", class_="date")
    authors = soup.select(".relations.persons a")

    return {
        "title": title.get_text(strip=True) if title else "",
        "year": year.get_text(strip=True) if year else "",
        "authors": [
            {
                "name": a.get_text(strip=True),
                "profile_url": urljoin(BASE_URL, a["href"]),
            }
            for a in authors
        ],
        "publicationUrl": url,
    }


def crawl_all_publications() -> List[Dict]:
    # Retrieve URL for the page that contains all the publications
    publication_url = get_publications_page_url()
    publication_links = crawl_publication_list(publication_url)

    data = []
    i = 1
    for link in publication_links:
        try:
            publication_data = crawl_individual_publication(link)
            print(publication_data)
            data.append(publication_data)
            i += 1
            if i == 3:
                break
        except Exception as e:
            print(f"Failed to crawl {link}", e)

    return data
