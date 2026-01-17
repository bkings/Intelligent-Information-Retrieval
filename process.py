import streamlit as st
from ir_core.crawler_main import crawl
from ir_core.index_manager import search

BASE_URL = "https://pureportal.coventry.ac.uk"
ORG_URL = (
    BASE_URL
    + "/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo"
)


def processQuery(userQuery: str):
    if not userQuery:
        st.info("Enter to search for publications.")
        return

    # results = search(userQuery)
    # if not results:
    #     st.warning("No matching publications found.")
    #     return

    # st.subheader(f"Showing results for {userQuery} ({len(results)} found)")
    st.subheader(f"Showing results for {userQuery}")
    crawl(BASE_URL, ORG_URL, False)

