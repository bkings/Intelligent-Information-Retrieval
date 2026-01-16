import streamlit as st
from components.search_bar import search_bar
from process import processQuery

st.title("🔍 Dig N Digest")

userQuery, searchClicked = search_bar()

if userQuery or searchClicked:
    processQuery(userQuery)