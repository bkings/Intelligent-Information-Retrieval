import requests
import time
import json
import logging

from datetime import datetime
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

from ir_core.index_manager import preprocess
from utils.util import extract_year

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WAIT_TIME = 5
DATA_PATH = Path("data")
DATA_PATH.mkdir(exist_ok=True)
INDEX_FILE = DATA_PATH / "publications.json"

unique_publications: set[str] = set()


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


def get_persons_url(driver: WebDriver, base_url: str) -> str:
    """Navigate to profiles tab"""
    print("Fetching profiles URL ...")
    driver.get(base_url)
    logger.info(f"In {WAIT_TIME} seconds ...")
    time.sleep(WAIT_TIME)
    remove_consent_overlay(driver)
    # Find the profile link
    profile_link = driver.find_element(
        By.CSS_SELECTOR, "#page-content .subMenu a[href*='persons']"
    )
    driver.execute_script("arguments[0].click();", profile_link)
    logger.info(f"In {WAIT_TIME} seconds ...")
    time.sleep(WAIT_TIME)
    print(f"Found Profiles url: {driver.current_url}")
    return driver.current_url


def get_publication_url(driver: WebDriver, base_url: str) -> str:
    """Navigate to publications tab"""
    print("Fetching publications URL ...")
    driver.get(base_url)
    logger.info(f"In {WAIT_TIME} seconds ...")
    time.sleep(WAIT_TIME)
    remove_consent_overlay(driver)
    # Find the publication link
    pub_link = driver.find_element(
        By.CSS_SELECTOR, "#page-content .subMenu a[href*='publication']"
    )
    driver.execute_script("arguments[0].click();", pub_link)
    logger.info(f"In {WAIT_TIME} seconds ...")
    time.sleep(WAIT_TIME)
    print(f"Found Publication url: {driver.current_url}")
    return driver.current_url


def retrieve_keywords(soup: BeautifulSoup) -> str:
    keywords_elem = soup.select(".keyword-group .relations.keywords span")
    if keywords_elem:
        return ",".join(k.get_text(strip=True) for k in keywords_elem)
    return None


def retrieve_fingerprints(driver: WebDriver) -> str:
    try:
        fingerprint_link = driver.find_element(
            By.CSS_SELECTOR, "#page-content .subMenu a[href*='/fingerprints']"
        )
        driver.execute_script("arguments[0].click();", fingerprint_link)
        logger.info("Retrieving fingerprints ...")
        logger.info(f"In {WAIT_TIME} seconds ...")
        time.sleep(WAIT_TIME)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        fingerprint_elem = soup.select(
            ".publication-fingerprints .concept_listing span.concept"
        )
        if fingerprint_elem:
            return ",".join(f.get_text(strip=True) for f in fingerprint_elem)
    except NoSuchElementException:
        print("No fingerprints")
    return None


def crawl_single_publication(driver: WebDriver, pub_url: str) -> Dict[str, Any]:
    """Crawl individual publication page for full details"""
    # Check if current publication has already been crawled
    if pub_url in unique_publications:
        logger.info(f"Skipping url: {pub_url} as its already crawled")
        return

    print(f"Crawling individual page {pub_url}")
    driver.get(pub_url)
    logger.info(f"In {WAIT_TIME} seconds ...")
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
        "keywords": "",
        "fingerprints": "",
        "content": "",
        "last_crawled": "",
        "year_only": "",
    }

    title_elem = soup.find("h1", id="firstheading") or soup.select_one("h1")
    pub_data["title"] = title_elem.get_text(strip=True) if title_elem else "No Title"
    author_links = soup.select(".introduction p a[href*='/en/persons']")

    # Verify if there is at least one member author
    if not author_links:
        return None

    for a in author_links:
        name = a.get_text(strip=True)
        if name and len(name) > 1:
            pub_data["authors"].append(name)
            pub_data["author_profiles"].append(a.get("href", ""))

    # Add non-member authors as well
    non_member_authors_p_tag = soup.select_one(".introduction .relations.persons")
    non_member_authors = "".join(
        non_member_authors_p_tag.find_all(string=True, recursive=False)
    ).strip()
    if non_member_authors:
        # non_member_authors_list = non_member_authors.strip(", ").split(",")
        pub_data["authors"].extend(
            a.strip() for a in non_member_authors.split(",") if a.strip()
        )

    year_elem = soup.select_one("[class*='details'] .properties .status td .date")
    if year_elem:
        logger.info("Year located.")
        pub_data["year"] = year_elem.get_text(strip=True) if year_elem else "N/A"
        pub_data["year_only"] = extract_year(pub_data["year"])

    abstract_elem = soup.select_one("[class*='abstract'], .description, p.abstract")
    if abstract_elem:
        logger.info("Abstract located.")
        pub_data["abstract"] = (
            abstract_elem.get_text(strip=True) if abstract_elem else ""
        )

    doi_elem = soup.select_one("a[title*='DOI'], [href*='doi.org']")
    if doi_elem:
        pub_data["doi"] = doi_elem.get("href", "") if doi_elem else ""

    pdf_elem = soup.select_one("a[href*='.pdf'], [title*='PDF']")
    if pdf_elem:
        pub_data["pdf_link"] = pdf_elem.get("href", "") if pdf_elem else ""

    keyword_elem = retrieve_keywords(soup)
    pub_data["keywords"] = keyword_elem if keyword_elem else ""

    fingerprint_elem = retrieve_fingerprints(driver)
    pub_data["fingerprints"] = fingerprint_elem if fingerprint_elem else ""

    pub_data["content"] = preprocess(
        f"{pub_data['title']} {' '.join(pub_data['authors'])} {pub_data['year']} {pub_data['abstract']} {pub_data['keywords'].replace(",", " ")} {pub_data['fingerprints'].replace(",", " ")}"
    )

    unique_publications.add(pub_url)
    pub_data["last_crawled"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info(f"LOGGER: Crawled details: {pub_data['title'][:50]} ... ")
    return pub_data


def crawl_all_pages(
    driver: WebDriver, wait: WebDriverWait, start_url: str
) -> List[Dict[str, Any]]:
    """Crawl all pages politely"""
    all_pubs = []
    current_url = start_url
    page_num = 0
    while current_url:
        print(f"Crawling all publications from page {page_num}: {current_url}")
        driver.get(current_url)
        logger.info(f"In {WAIT_TIME} seconds ...")
        time.sleep(WAIT_TIME)
        remove_consent_overlay(driver)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        pub_links = soup.select("#main-content .list-results .list-result-item h3 a")

        # Only for testing
        # i = 1

        for link_elem in pub_links:
            pub_url = link_elem.get("href")
            if pub_url and not pub_url.startswith("https://"):
                pub_url = "https://pureportal.coventry.ac.uk" + pub_url
            if pub_url:
                pub_data = crawl_single_publication(driver, pub_url)
                if pub_data:
                    all_pubs.append(pub_data)
                # time.sleep(WAIT_TIME)
                # logger.info(f"Sleeping for {WAIT_TIME} seconds ...")

            # if i == 1:
            #     break
            # i += 1

        # Only For testing
        # if page_num == 1:
        #     page_num = 6

        # Handling pagination
        try:
            # Only for testing
            # if page_num != 0:
            #     current_url_page_no = current_url[-1]
            #     replace_string = "page=" + current_url_page_no
            #     replace_to = "page=" + str(page_num)
            #     current_url = current_url.replace(replace_string, replace_to)

            # Return back to home url to access pagination after being directed to single publication page
            # If multiple authors have same publication then we won't re-crawl and as a result we will not be directed to that page
            if driver.current_url != current_url:
                driver.get(current_url)
                logger.info(f"In {WAIT_TIME} seconds ...")
                time.sleep(WAIT_TIME)
                remove_consent_overlay(driver)
            print(f"Current url {driver.current_url}")

            try:
                next_btn_exists = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".pages .nextLink")
                    )
                )
            except TimeoutException:
                next_btn_exists = False

            if next_btn_exists:
                next_page_btn = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            ".pages .nextLink, a[rel='next'], .pagination .next",
                        )
                    )
                )
                next_url = next_page_btn.get_attribute("href")

                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
            else:
                current_url = None

        except Exception as e:
            print("Error during crawl", e)
            current_url = None

    return all_pubs


def crawl_all_profiles(
    driver: WebDriver, wait: WebDriverWait, profiles_url: str
) -> List[Dict[str, Any]]:
    pubs_from_all_profiles = []
    print(f"Crawling all profiles from {profiles_url}")
    driver.get(profiles_url)
    logger.info(f"In {WAIT_TIME} seconds ...")
    time.sleep(WAIT_TIME)
    remove_consent_overlay(driver)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    profile_links = soup.select("#main-content .grid-results h3 a")

    # Only for testing (i value)
    # i = 1

    for link_elem in profile_links:
        try:
            # if i in [1, 2, 10]:
            # if i in [10]:
            profile_url = link_elem.get("href")
            if profile_url and not profile_url.startswith("https://"):
                profile_url = "https://pureportal.coventry.ac.uk" + profile_url
            if profile_url:
                start_url = profile_url + "publications"
                all_publications = crawl_all_pages(driver, wait, start_url)
                pubs_from_all_profiles.extend(all_publications)

        # if i == 3:
        #     break

        # i += 1
        except Exception as e:
            print(f"Error in profile crawl {link_elem}:", e)
            continue

    return pubs_from_all_profiles


def crawl(base_url: str, org_url: str, headless: bool = True) -> List[Dict[str, Any]]:
    """Entry point for the crawler
    Crawl all pages, handle paginations and save indexes"""
    if not robots_txt_satisfied(base_url):
        raise ValueError("Crawling disallowed by robots.txt")

    driver, wait = setup_driver(headless)
    print("Driver configuration complete.")
    try:
        profiles_url = get_persons_url(driver, org_url)
        all_publications = crawl_all_profiles(driver, wait, profiles_url)
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
