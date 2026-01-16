from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
import time

import requests
from bs4 import BeautifulSoup

WAIT_TIME_IN_SECONDS = 5


def crawl_page(url):
    print()


def crawl_pages(baseUrl):
    chrome_options = Options()
    chrome_options.binary_location = (
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    )

    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)

    print("Crawling initiated ...")
    driver.get(baseUrl)
    print(f"Waiting for {WAIT_TIME_IN_SECONDS} seconds ...")
    time.sleep(3)

    target_link = None

    try:
        research_links = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#page-content .subMenu a")
            )
        )
        print(len(research_links))

        for link in research_links:
            href = link.get_attribute("href")
            print(href)
            if href:
                href_lower = href.lower()
                if "publication" in href_lower:
                    target_link = link
                    break

    except Exception as e:
        print("Could not find the link", e)
        driver.quit()
        return

    if not target_link:
        raise Exception("Publications link could not be reached.")

    remove_overlay(driver)

    # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link)
    driver.execute_script("arguments[0].click();", target_link)
    # target_link.click()
    publications_url = driver.current_url
    print(f"Current url: {publications_url}")
    crawl_all_publications(driver, wait, publications_url)


def remove_overlay(driver: WebDriver):
    try:
        driver.execute_script(
            """
            var overlay = document.querySelector('.onetrust-pc-dark-filter');
            if (overlay) overlay.remove();
            """
        )
    except:
        pass


def crawl_all_publications(
    driver: WebDriver, wait: WebDriverWait, publications_url: str
):
    print(f"Crawling publication url: {publications_url}")
    driver.get(publications_url)
    print(f"Waiting for {WAIT_TIME_IN_SECONDS} seconds")
    time.sleep(3)

    try:
        print(driver.title)
        publication_links = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "#main-content .list-results .list-result-item h3 a")
            )
        )
        print(len(publication_links))

        i = 1
        for author_link in publication_links:
            print(f"Getting publication: {i}")
            href = author_link.get_attribute("href")
            print(href)
            i += 1
            if i == 2:
                break

    except Exception as e:
        print("Error getting publication urls", e)
        driver.quit()
        return


def crawl_all_publications_bs(publication_url: str):
    print(f"Crawling publication url: {publication_url}")
    browser = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    }
    try:
        r = requests.get(
            publication_url, headers=browser, timeout=10, allow_redirects=True
        )
        r.raise_for_status()
        bs4 = BeautifulSoup(r.text, "html.parser")

        title_tag = bs4.find("h1", id="firstheading")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        print(title)
    except Exception as e:
        print("Error", e)
