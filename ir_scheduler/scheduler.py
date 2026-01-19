import schedule
import time

from ir_core.crawler_main import crawl

BASE_URL = "https://pureportal.coventry.ac.uk"
ORG_URL = (
    BASE_URL
    + "/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo"
)


def job():
    print("Weekly crawl starting ...")
    crawl(BASE_URL, ORG_URL, False)
    print("Crawl successful.")


schedule.every().sunday.at("00:24").do(job)

if __name__ == "__main__":
    print("Scheduler running ... Ctrl+C to stop")
    while True:
        schedule.run_pending()
        time.sleep(60)
