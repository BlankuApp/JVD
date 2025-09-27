import os
import json

import streamlit as st

from src.db.db_word import (
    add_user_word_card,
    check_user_word_card,
    get_user_word_cards,
    remove_user_word_card,
)
from src.word.JPWord import JPWord
from src.word.JPWord2 import JPWord2

auth = st.session_state.get("auth", None)


def fetch_and_show_word():
    with open("resources/words/" + st.query_params["w"] + ".json", "r", encoding="utf-8") as file:
        raw_data = file.read()
        json_data = json.loads(raw_data)
        version = json_data.get("version")
        w = None
        if version == "0.1.1":
            w = JPWord.model_validate_json(raw_data)
        elif version == "0.2.0":
            w = JPWord2.load_from_json(json_data["word"])
        if w:
            w.show_in_streamlit(st, auth)


@st.cache_data(ttl=3600)
def get_words() -> list[dict]:
    words = []
    json_files = [f for f in os.listdir("resources/words") if f.endswith(".json")]
    for json_file in json_files:
        with open(os.path.join("resources/words", json_file), "r", encoding="utf-8") as file:
            raw_data = file.read()
            json_data = json.loads(raw_data)
            version = json_data.get("version")
            print(f"Loading word '{json_data['word']}' version {version}")
            w = None
            if version == "0.1.1":
                w = JPWord.model_validate_json(raw_data)
            if version == "0.2.0":
                w = JPWord2.load_from_json(json_data["word"])
            if w:
                words.append(dict(word=w.word, level=w.jlpt_level))
    return words


if "w" in st.query_params:
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button(":arrow_left: Back to Vocabularies"):
            st.query_params.pop("w")
            st.rerun()
        card_added = check_user_word_card(auth, st.query_params["w"]) if auth else False
        if card_added:
            if st.button(":star: remove from My Words"):
                if auth:
                    result = remove_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to manage your words.", icon="❌")
        else:
            if st.button(":star: Add to My Words", type="primary"):
                if auth:
                    result = add_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to add words to your list.", icon="❌")
    fetch_and_show_word()
else:
    user_word_cards = get_user_word_cards(auth) if auth else []
    marked_words = [w.get("key") for w in user_word_cards] if user_word_cards else []
    words = get_words()
    st.markdown("# JLPT Vocabularies")

    for level in [4, 3, 2]:
        with st.expander(f"N{level} Vocabularies"):
            with st.container(horizontal=True):
                for w in words:
                    if w.get("level") == level:
                        word = str(w.get("word", ""))
                        if st.button(word, type="primary" if word in marked_words else "secondary"):
                            st.query_params.update({"w": word})
                            st.rerun()
