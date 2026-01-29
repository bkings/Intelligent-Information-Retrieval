import streamlit as st
import time
from ir_core.index_manager import search, load_index
from ir_core.evaluation import evaluate_search


def processQuery(userQuery: str):
    if not userQuery:
        st.error("Enter query to search for publications.")
        return

    search_type, results = search(userQuery)
    if not results:
        st.warning("No matching publications found.")
        return
    with st.status("Processing ...") as status:
        if search_type == "PI":
            status.update(label="Building positional index ...")
            time.sleep(0.3)
            status.update(label="Loading indexes ...")
            time.sleep(0.2)
            status.update(label="Phrase Searching and returning results ...")
            time.sleep(0.2)
            status.update(label="Search complete", state="complete", expanded=False)
        elif search_type == "TFIDF":
            status.update(label="Creating TF-IDF index ...")
            time.sleep(0.3)
            status.update(label="Calculating cosine similarities ...")
            time.sleep(0.2)
            status.update(label="Searching and returning results ...")
            time.sleep(0.2)
            status.update(label="Search complete", state="complete", expanded=False)

    if st.checkbox("Show evaluation metrics"):
        metrics = evaluate_search(userQuery, results, load_index())
        st.json(metrics)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precision", f"{metrics['precision']:.2f}")
        col2.metric("Recall", f"{metrics['recall']:.2f}")
        col3.metric("F1 Score", f"{metrics['f1']:.2f}")
        col4.metric("Accuracy", f"{metrics['accuracy']:.2f}")

    st.subheader(f"Showing results for '{userQuery}' ({len(results)} retrieved)")
    for i, pub in enumerate(results, 1):
        score_str = f"Relevancy: {pub['relevancy_score']:.3f}"
        st.caption(
            f"Phrase matches: {pub.get("phrase_matches", 0)} | Score: {score_str}"
        )

        pub_year = pub["year"]
        if pub_year:
            pub_year = f"**[{pub_year}]**"

        with st.expander(
            f"{i}. {pub_year} {pub['title'][:100]} ...",
            expanded=True,
            icon="👉",
        ):
            if pub["author_profiles"]:
                fullRow = ""
                for profile in pub["author_profiles"]:
                    authorLink = f"[{profile.split('/')[-2].replace("-", " ").title()}]({profile})"
                    fullRow = fullRow + ", " + authorLink
                if fullRow:
                    st.markdown(f"**Authors:** {(fullRow.strip(","))}")

            if pub.get("abstract"):
                with st.expander(f"**Snippet:** {pub['abstract'][:115]}..."):
                    st.write(pub["abstract"])

            cols = st.columns(3)

            if pub["pub_link"]:
                cols[0].markdown(f"[Publication]({pub['pub_link']})")
            if pub["doi"]:
                cols[1].markdown(f"[DOI]({pub['doi']})")
            if pub["pdf_link"]:
                cols[2].markdown(f"[PDF]({pub['pdf_link']})")

            pubKeywords = pub["keywords"]
            pubFingerprints = pub["fingerprints"]
            keywords = []
            fingerprints = []

            if pubKeywords:
                keywords = pubKeywords.split(",")[:2]

            if pubFingerprints:
                fingerprints = pubFingerprints.split(",")[:2]

            if keywords or fingerprints:
                combined = [*keywords, *fingerprints]
                st.pills(
                    "Related keywords",
                    combined,
                    selection_mode="single",
                    key=f"pill{i}",
                )
