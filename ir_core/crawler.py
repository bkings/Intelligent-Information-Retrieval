import requests
import time
import json
import re
import logging

from typing import List, Dict, Any
from pathlib import Path
from robotexclusionrulesparser import RobotExclusionRulesParser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WAIT_TIME = 5
DATA_PATH = Path("data")
DATA_PATH.mkdir(exist_ok=True)
INDEX_FILE = DATA_PATH / "publications.json"


def robots_txt_satisfied(base_url: str) -> bool:
    """
    Return True if crawling `path` is allowed by robots.txt
    for user-agent '*'.
    """
    parser = RobotExclusionRulesParser()
    try:
        robots_url = base_url.rstrip("/") + "/robots.txt"
        resp = requests.get(robots_url, timeout=10)

        # If robots.txt cannot be fetched, allow by convention
        if resp.status_code != 200:
            return True
        parser.parse(resp.text)
        return parser.is_allowed("*", "/en/organisations")
    except requests.RequestException:
        # Network failure → default allow
        return True


def setup_driver(headless: bool = True) -> tuple[webdriver.Chrome, WebDriverWait]:
    """Configure driver properties for crawling"""
    print("Configuring driver ...")
    options = Options()
    options.binary_location = (
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    )
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver, WebDriverWait(driver, 15)


def remove_consent_overlay(driver):
    """Remove cookie banners politely."""
    driver.execute_script(
        """
        const overlays = document.querySelectorAll('.onetrust-pc-dark-filter, [id*="consent"], [class*="overlay"]');
        overlays.forEach(o => o.remove());
    """
    )


def preprocess(text: str) -> str:
    """Tokenize, lowercase, remove punctuations"""
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())  # Normalizing the whitespaces


def extract_publication_data(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract title, authors, year, pub_link, author_profiles from list page"""
    print("Data extraction for each publication started ...")
    pubs = []
    items = soup.select("#main-content .list-results .list-result-item")

    i = 0

    for item in items:
        title_elem = item.select_one("h3 a")
        if not title_elem:
            continue
        pub_data = {
            "title": title_elem.text.strip(),
            "pub_link": title_elem.get("href", ""),
            "authors": [],
            "year": "",
            "author_profiles": [],
        }
        author_links = item.select("a[href*='/en/persons']")
        for a in author_links[:5]:
            name = a.text.strip()
            profile = a.get("href", "")
            pub_data["authors"].append(name)
            pub_data["author_profiles"].append(profile)

        # Fetch year from metadata if it's present
        year_elem = item.select_one(".result-meta-data time, [class*='year']")
        pub_data["year"] = year_elem.text.strip() if year_elem else "N/A"
        # At least one of the co-authors is a member
        if not author_links:
            break
        pubs.append(pub_data)

        if i == 2:
            break
        i += 1

    return pubs


def get_publications_url(driver: WebDriver, base_url: str) -> str:
    """Navigate to publications tab"""
    print("Fetching publications URL ...")
    driver.get(base_url)
    time.sleep(WAIT_TIME)
    remove_consent_overlay(driver)
    # Find the publication link
    pub_link = driver.find_element(
        By.CSS_SELECTOR, "#page-content .subMenu a[href*='publication']"
    )
    driver.execute_script("arguments[0].click();", pub_link)
    time.sleep(WAIT_TIME)
    print(f"Found Publication url: {driver.current_url}")
    return driver.current_url


def crawl_single_publication(driver: WebDriver, pub_url: str) -> Dict[str, Any]:
    """Crawl individual publication page for full details"""
    driver.get(pub_url)
    time.sleep(WAIT_TIME)
    remove_consent_overlay(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    pub_data = {
        "title": "",
        "pub_link": pub_url,
        "authors": [],
        "author_profiles": [],
        "year": "",
        "abstract": "",
        "doi": "",
        "pdf_link": "",
        "content": "",
    }

    title_elem = soup.find("h1", id="firstheading") or soup.select_one("h1")
    pub_data["title"] = title_elem.get_text(strip=True) if title_elem else "No Title"
    author_links = soup.select("a[href*='/en/persons']")
    for a in author_links:
        name = a.get_text(strip=True)
        if name and len(name) > 1:
            pub_data["authors"].append(name)
            pub_data["author_profiles"].append(a.get("href", ""))

    year_elem = soup.select_one("time, .result-meta-data [datetime], [class*='year']")
    pub_data["year"] = year_elem.get(
        "datetime", year_elem.get_text(strip=True) if year_elem else "N/A"
    )

    abstract_elem = soup.select_one("[class*='abstract'], .description, p.abstract")
    pub_data["abstract"] = abstract_elem.get_text(strip=True) if abstract_elem else ""

    doi_elem = soup.select_one("a[title*='DOI'], [href*='doi.org']")
    pub_data["doi"] = doi_elem.get("href", "") if doi_elem else ""

    pdf_elem = soup.select_one("a[href*='.pdf'], [title*='PDF']")
    pub_data["pdf_link"] = pdf_elem.get("href", "") if pdf_elem else ""

    pub_data["content"] = preprocess(
        f"{pub_data['title']} {' '.join(pub_data['authors'])} {pub_data['year']} {pub_data['abstract']}"
    )

    print(f"Crawled details: {pub_data['title'][:50]} ... ")
    logger.info(f"LOGGER: Crawled details: {pub_data['title'][:50]} ... ")


def crawl_all_pages(
    driver: WebDriver, wait: WebDriverWait, start_url: str
) -> List[Dict[str, Any]]:
    """Crawl all pages politely"""
    all_pubs = []
    current_url = start_url
    page_num = 1
    while current_url:
        print(f"Crawling page {page_num}: {current_url}")
        driver.get(current_url)
        time.sleep(WAIT_TIME)
        remove_consent_overlay(driver)

        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            page_pubs = extract_publication_data(soup)
            all_pubs.extend(page_pubs)
            print(f"Extracted {len(page_pubs)} publications from page {page_num}")

            # Look if next page is present
            next_button = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a[rel='next'], .pagination .next")
                )
            )
            next_url = next_button.get_attribute("href")
            if not next_url or next_url == current_url:
                break
            # current_url = next_url
            page_num += 1
            driver.execute_script("arguments[0].scrollInView();", next_button)
            time.sleep(WAIT_TIME)
        except (TimeoutException, NoSuchElementException):
            print("No more pages or load timeout")
            break
        except Exception as e:
            print("Error during crawl", e)
            break

    return all_pubs


def crawl(base_url: str, org_url: str, headless: bool = True) -> List[Dict[str, Any]]:
    """Entry point for the crawler
    Crawl all pages, handle paginations and save indexes"""
    if not robots_txt_satisfied(base_url):
        raise ValueError("Crawling disallowed by robots.txt")

    driver, wait = setup_driver(headless)
    print("Driver configuration complete.")
    try:
        pubs_url = get_publications_url(driver, org_url)
        all_publications = crawl_all_pages(driver, wait, pubs_url)
        unique_publications = []
        seen_titles = set()
        for pub in all_publications:
            if pub["title"] not in seen_titles:
                seen_titles.add(pub["title"])
                unique_publications.append(pub)
        with open(INDEX_FILE, "w") as f:
            json.dump(unique_publications, f, indent=2)
        print(f"Crawled and saved {len(unique_publications)} unique publications")
        return unique_publications
    except Exception as e:
        print("Error while crawling", e)
    finally:
        driver.quit()
