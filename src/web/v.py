import os

import streamlit as st

from src.word.JPWord import JPWord
from src.db import db_word


auth = st.session_state.get("auth", None)


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
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button(":arrow_left: Back to Vocabularies"):
            st.query_params.pop("w")
            st.rerun()
        card_added = db_word.check_user_word_card(auth, st.query_params["w"]) if auth else False
        if card_added:
            if st.button(":star: remove from My Words"):
                if auth:
                    result = db_word.remove_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to manage your words.", icon="❌")
        else:
            if st.button(":star: Add to My Words", type="primary"):
                if auth:
                    result = db_word.add_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to add words to your list.", icon="❌")
    fetch_and_show_word()
else:
    user_word_cards = db_word.get_user_word_cards(auth) if auth else []
    marked_words = [w.get("key") for w in user_word_cards] if user_word_cards else []
    st.markdown("# JLPT Vocabularies")
    with st.expander("N3 Vocabularies"):
        with st.container(horizontal=True):
            for file in n3_vocabulary_files:
                if st.button(file, type="primary" if file in marked_words else "secondary"):
                    st.query_params.update({"w": file})
                    st.rerun()

    with st.expander("N2 Vocabularies"):
        with st.container(horizontal=True):
            for file in n2_vocabulary_files:
                if st.button(file, type="primary" if file in marked_words else "secondary"):
                    st.query_params.update({"w": file})
                    st.rerun()
