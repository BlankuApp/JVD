import streamlit as st
import os
from src.word import JPWord
from random import choice


def select_random():
    current_word = st.session_state.selection
    new_set = set(json_files) - {current_word}
    if new_set:
        st.session_state.selection = choice(list(new_set))
        st.set_page_config(page_title=f"N3 Vocabularies - {st.session_state.selection}", layout="wide")


# Load JSON files
json_files = [f[:-5] for f in os.listdir("resources/words/n3") if f.endswith(".json")]
json_files.sort()


# Sidebar widgets
st.sidebar.selectbox(label="Select", options=json_files, index=0, key="selection", label_visibility="collapsed")
st.sidebar.button("Pick Random", on_click=select_random, width="stretch")
st.set_page_config(page_title=f"N3 Vocabularies - {st.session_state.selection}", layout="wide")

# Load and display the selected word
selected_file = f"Word/{st.session_state.selection}.json"
with open(selected_file, "r", encoding="utf-8") as file:
    w = JPWord.model_validate_json(file.read())
w.show_in_streamlit(st)
