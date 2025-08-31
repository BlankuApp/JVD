import streamlit as st
import os
from src.word import JPWord


def fetch_and_show_word():
    json_files = [f[:-5] for f in os.listdir("Word") if f.endswith(".json")]
    json_files.sort()
    if st.query_params["word"] in json_files:
        with open("Word/" + st.query_params["word"] + ".json", "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
        w.show_in_streamlit(st)


if "word" in st.query_params:
    fetch_and_show_word()
else:
    st.title("Japanese Video Dictionary")
