import streamlit as st
from components.search_bar import search_bar
from process import processQuery
from ir_core.crawler_main import crawl
from ir_core.index_manager import load_index
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

import pandas as pd
import numpy as np


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

docs = load_index()
if not docs:
    st.warning("Data not indexed. **Run crawler** manually from the sidebar.")

# Sidebar tab
page = st.sidebar.selectbox("Navigate", ["Search", "Summary"])

# Sidebar
with st.sidebar:
    st.header("Crawler status")
    if st.button("Update index (Run Crawler)"):
        with st.spinner("Crawling in progress ..."):
            crawl(BASE_URL, ORG_URL, False)
        st.success("Crawl successful. Index updated!")
    # docs = load_index()
    if docs:
        num_pubs = len(docs)
        last_crawled = docs[0]["last_crawled"]
        st.metric("Indexed publications", num_pubs)
        st.info(f"Last crawled: {last_crawled}")
    st.info("Crawl scheduled to run weekly")


if page == "Search":
    userQuery, searchClicked = search_bar()
    if userQuery or searchClicked:
        try:
            processQuery(userQuery)
        except Exception as e:
            print("Error searching: ", e)
            st.error("Something went wrong. Try again later!")
elif page == "Summary":
    st.header("📊 Crawling & Publication Summary")
    st.markdown("**Generated from current index**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Publications", len(docs))
    with col2:
        unique_authors = len(set(a for pub in docs for a in pub.get("authors", [])))
        st.metric("Unique Authors", unique_authors)

    st.subheader("Crawl Summary")
    avg_authors = np.round(np.mean([len(p.get("authors", [])) for p in docs]), 1)
    st.json(
        {
            "Total Detail Pages": len(docs),
            "Avg Authors/Pub (Collaborations)": avg_authors,
        }
    )

    # Top Authors
    st.subheader("Top Authors")
    author_pubs = Counter()
    for pub in docs:
        # Limit authors per publication
        for author in pub.get("authors", [])[:10]:
            author_pubs[author] += 1
    top_authors = author_pubs.most_common(5)
    df_top = pd.DataFrame(top_authors, columns=["Author", "Publications"])
    # Start index from 1 instead of 0
    df_top.index = np.arange(1, len(df_top) + 1)
    st.dataframe(df_top, width="stretch")

    ## Term(words) Trends
    st.subheader("🏷️ Top words By Tf-Idf Scores")
    all_content = " ".join(pub.get("content", "") for pub in docs)
    vectorizer = TfidfVectorizer(
        max_features=20, stop_words="english", ngram_range=(1, 2)
    )
    try:
        tfidf = vectorizer.fit_transform([all_content])
        keywords = vectorizer.get_feature_names_out()
        scores = tfidf.toarray()[0]
        df_keywords = pd.DataFrame({"Word": keywords, "Tf-Idf Score": scores}).sort_values(
            "Tf-Idf Score", ascending=False
        )
        st.bar_chart(df_keywords.set_index("Word"))
        st.dataframe(df_keywords, hide_index=True)
    except Exception as e:
        print("Error: ", e)
        st.info("Insufficient content for keywords.")

    st.subheader("Publications by Year")
    years = [pub.get("year_only", "N/A") for pub in docs]
    year_counts = Counter(y for y in years if y != "N/A")
    df_years = pd.DataFrame(
        list(year_counts.items()), columns=["Year", "Count"]
    ).sort_values("Year")
    st.bar_chart(df_years.set_index("Year"))
