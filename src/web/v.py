import os

import streamlit as st

# from main import get_auth

from src.word.JPWord import JPWord

from streamlit_cookies_controller import CookieController

controller = CookieController()


auth = controller.get("auth")
if auth:
    st.session_state["auth"] = auth


# Load JSON files
n3_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n3") if f.endswith(".json")]
n3_vocabulary_files.sort()

n2_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n2") if f.endswith(".json")]
n2_vocabulary_files.sort()


def fetch_and_show_word():
    w = None
    if st.query_params["w"] in n3_vocabulary_files:
        with open("resources/words/n3/" + st.query_params["w"] + ".json", "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
    elif st.query_params["w"] in n2_vocabulary_files:
        with open("resources/words/n2/" + st.query_params["w"] + ".json", "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
    if w:
        w.show_in_streamlit(st, auth)


if "w" in st.query_params:
    if st.button(":arrow_left: Back to Vocabularies"):
        st.query_params.pop("w")
        st.rerun()
    fetch_and_show_word()
else:
    st.markdown("# JLPT Vocabularies")
    with st.expander("N3 Vocabularies"):
        with st.container(horizontal=True):
            for file in n3_vocabulary_files:
                if st.button(file):
                    st.query_params.update({"w": file})
                    st.rerun()

    with st.expander("N2 Vocabularies"):
        with st.container(horizontal=True):
            for file in n2_vocabulary_files:
                if st.button(file):
                    st.query_params.update({"w": file})
                    st.rerun()
