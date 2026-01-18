import streamlit as st
from ir_core.index_manager import search

def processQuery(userQuery: str):
    if not userQuery:
        st.info("Enter to search for publications.")
        return

    results = search(userQuery)
    if not results:
        st.warning("No matching publications found.")
        return

    st.subheader(f"Showing results for {userQuery} ({len(results)} found)")
    for i, pub in enumerate(results, 1):
        score_str = f"Relevancy: {pub['relevancy_score']:.3f}"
        with st.expander(f"{i}. {pub['title']} [{score_str}]"):
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
