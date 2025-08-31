import streamlit as st

main_page = st.Page("src/web/main_page.py", title="Main Page", icon="🏠")
jlpt_vocabularies = st.Page("src/web/Vocabularies.py", title="JLPT Vocabularies", icon="📚")
app = st.navigation(pages=[main_page, jlpt_vocabularies])
app.run()
