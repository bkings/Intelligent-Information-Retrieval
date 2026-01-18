import streamlit as st


def search_bar(
    placeholder: str = "Enter to search ...", button_label: str = "🔍"
) -> tuple[str, bool]:

    st.markdown("""
    <style>
    [data-baseweb="base-input"]{
    /*background:linear-gradient(to bottom, #352f2f 0%, #1b1a1a 90%);*/
    border: 2px;
    border-radius: 3px;
    }

    input[class]{
    /*font-weight: bold;*/
    font-size: 110%;
    }
    </style>
    """, unsafe_allow_html=True)

    queryCol, buttonCol = st.columns([6, 1], gap=None)

    with queryCol:
        userQuery = st.text_input(
            "Search", placeholder=placeholder, label_visibility="collapsed"
        )

    with buttonCol:
        search_clicked = st.button(button_label)

    return userQuery.strip(), search_clicked
