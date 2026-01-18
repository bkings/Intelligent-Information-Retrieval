import streamlit as st
from components.search_bar import search_bar
from process import processQuery
from ir_core.crawler_main import crawl
from ir_core.index_manager import load_index

BASE_URL = "https://pureportal.coventry.ac.uk"
ORG_URL = (
    BASE_URL
    + "/en/organisations/ics-research-centre-for-computational-science-and-mathematical-mo"
)

st.set_page_config(page_title="🔍 Dig N Digest", layout="wide")
st.title("🔍 Dig N Digest")
st.markdown(
    "Search publications by Coventry University's Research Centre for Computational Science and Mathematical Modelling."
)

# Sidebar
with st.sidebar:
    st.header("Crawler status")
    if st.button("Update index (Run Crawler)"):
        with st.spinner("Crawling in progress ..."):
            crawl(BASE_URL, ORG_URL, False)
        st.success("Crawl successful. Index updated!")
    num_pubs = len(load_index())
    st.metric("Indexed publications", num_pubs)
    st.info("Crawl scheduled to run weekly")

userQuery, searchClicked = search_bar()

if userQuery or searchClicked:
    try:
        processQuery(userQuery)
    except Exception as e:
        print("Error searching: ", e)
        st.error("Something went wrong. Try again later!")
