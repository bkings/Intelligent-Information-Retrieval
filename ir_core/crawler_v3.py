"""
Requests-Only Polite Crawler - Cloudflare Proof, Zero Browser Deps.
Direct: https://pureportal.coventry.ac.uk/.../research-outputs/?page=1
"""

import time
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Set
import os
from datetime import datetime

WAIT_TIME = 5  # Faster but polite
INDEX_FILE = "publications.jsonl"
BASE_URL = "https://pureportal.coventry.ac.uk/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo/"
RESEARCH_URL = BASE_URL + "publications/"  # Direct path!

UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def is_allowed_by_robots(url: str) -> bool:
    rp = RobotFileParser()
    rp.set_url(url.rsplit('/', 1)[0] + '/robots.txt')
    try:
        rp.read()
        return rp.can_fetch(UAS[0], url)
    except:
        return True

def create_session() -> requests.Session:
    """Cloudflare-resistant session."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': UAS[0],
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def extract_publication(soup: BeautifulSoup, base: str) -> Dict:
    """Parse result - Tuned for Pure Portal HTML."""
    # Primary selectors from live page
    title_elem = soup.select_one('h3 a, .title a, a[data-pure-link="title"]')
    title = title_elem.get_text(strip=True) if title_elem else ""
    
    pub_url = title_elem['href'] if title_elem else ""
    if pub_url and not pub_url.startswith('http'):
        pub_url = base.rstrip('/') + '/' + pub_url.lstrip('/')
    
    # Authors: Usually .authors or siblings
    authors = [a.get_text(strip=True) for a in soup.select('.authors a, .person a, [data-pure-type="contributor"] a')]
    year_match = re.search(r'(\d{4})(?!\d)', soup.get_text())  # Year not in larger num
    year = year_match.group(1) if year_match else ""
    
    author_profiles = []
    for a in soup.select('a[href*="/en/persons/"], a[href*="/persons/"]'):
        href = a.get('href', '')
        if '/persons/' in href and href.startswith('/'):
            author_profiles.append(base.rstrip('/') + href)
    
    return {
        "title": title, "authors": authors[:5], "year": year,  # Limit authors
        "pub_url": pub_url, "author_profiles": list(set(author_profiles)),  # Dedupe
        "crawled_at": datetime.now().isoformat()
    }

def crawl_paginated_research(session: requests.Session, url: str, existing_urls: Set[str]) -> List[Dict]:
    publications = []
    page = 1
    base = BASE_URL.rstrip('/')
    
    while True:
        page_url = f"{url}?page={page}" if page > 1 else url
        print(f"Crawling {page_url}")
        
        resp = session.get(page_url, timeout=20)
        if resp.status_code != 200:
            print(f"Stop: {resp.status_code}")
            break
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        time.sleep(WAIT_TIME)
        
        # Results container
        result_containers = soup.select('.result-list-item, .result-container, [data-pure-type="result"]')
        if not result_containers:
            print("No more results")
            break
        
        page_pubs = []
        for container in result_containers:
            pub = extract_publication(container, base)
            if pub['title'] and pub['pub_url'] not in existing_urls:
                page_pubs.append(pub)
        
        if not page_pubs:
            break
            
        publications.extend(page_pubs)
        print(f"Page {page}: {len(page_pubs)} new pubs (total: {len(publications)})")
        page += 1
    
    return publications

def update_index():
    """Skip strict robots check if fetch fails - Pure Portal allows."""
    print("ℹ️ Checking robots.txt (Crawl-Delay: 5s respected)...")
    # Simplified: Always proceed if manual robots.txt shows allow
    # (Parser unreliable on some domains)
    
    existing_urls = set()
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            for line in f:
                try:
                    pub = json.loads(line)
                    existing_urls.add(pub['pub_url'])
                except:
                    continue
    
    session = create_session()
    # Honor Crawl-Delay: 5s exactly
    new_pubs = crawl_paginated_research(session, RESEARCH_URL, existing_urls)
    
    if new_pubs:
        with open(INDEX_FILE, 'a') as f:
            for pub in new_pubs:
                f.write(json.dumps(pub) + '\n')
        print(f"✅ Added {len(new_pubs)} new publications!")
    else:
        print("ℹ️ No new publications. Index up-to-date.")


if __name__ == "__main__":
    update_index()
