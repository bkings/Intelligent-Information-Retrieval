import streamlit as st
import time
from ir_core.index_manager import search, load_index
from ir_core.evaluation import evaluate_search


def processQuery(userQuery: str):
    if not userQuery:
        st.warning("Enter query to search for publications.")
        return

    search_type, results = search(userQuery)
    if not results:
        st.warning("No matching publications found.")
        return
    with st.status("Processing ...") as status:
        if search_type == "PI":
            st.write("Building positional index ...")
            time.sleep(0.1)
            st.write("Loading indexes ...")
            time.sleep(0.1)
            st.write("Phrase Searching and returning results ...")
            time.sleep(0.1)
            status.update(label="Search complete", state="complete", expanded=False)
        elif search_type == "TFIDF":
            st.write("Creating TF-IDF index ...")
            time.sleep(0.1)
            st.write("Calculating cosine similarities ...")
            time.sleep(0.1)
            st.write("Searching and returning results ...")
            time.sleep(0.1)
            status.update(label="Search complete", state="complete", expanded=False)

    if st.checkbox("Show evaluation metrics"):
        metrics = evaluate_search(userQuery, results, load_index())
        st.json(metrics)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precision", f"{metrics['precision']:.2f}")
        col2.metric("Recall", f"{metrics['recall']:.2f}")
        col3.metric("F1 Score", f"{metrics['f1']:.2f}")
        col4.metric("Accuracy", f"{metrics['accuracy']:.2f}")

    st.subheader(f"Showing results for {userQuery} ({len(results)} found)")
    for i, pub in enumerate(results, 1):
        score_str = f"Relevancy: {pub['relevancy_score']:.3f}"
        st.caption(
            f"Phrase matches: {pub.get("phrase_matches", 0)} | Score: {score_str}"
        )
        with st.expander(f"{i}. {pub['title']}", expanded=True, icon="👉"):
            st.write(
                "**Authors:** "
                + (
                    ", ".join(pub["authors"][:5])
                    + (", et al." if len(pub["authors"]) > 5 else "")
                )
            )
            st.write(f"**Year:** {pub['year']}")
            if pub.get("snippet"):
                st.write("**Snippet:**" + pub["snippet"])
            if pub.get("abstract"):
                with st.expander("Full Abstract"):
                    st.write(pub["abstract"])

            cols = st.columns(3)

            if pub["pub_link"]:
                cols[0].markdown(f"[Publication]({pub['pub_link']})")
            if pub["doi"]:
                cols[1].markdown(f"[DOI]({pub['doi']})")
            if pub["pdf_link"]:
                cols[2].markdown(f"[PDF]({pub['pdf_link']})")
            if pub["author_profiles"]:
                st.markdown("**Author Profiles:**")
                for profile in pub["author_profiles"]:
                    st.markdown(f"[{profile.split('/')[-2].title()}]({profile})")
