import streamlit as st
from ir_core.crawler import crawl
from ir_core.crawler_v1 import crawl_pages

BASE_URL = "https://pureportal.coventry.ac.uk"
ORG_URL = (
    BASE_URL
    + "/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo"
)

def processQuery(userQuery:str):
    st.subheader(f"Showing results for {userQuery}")
    crawl(BASE_URL, ORG_URL, False)
    # crawl_pages(ORG_URL)