import streamlit as st
import os
from src.word.JPWord import JPWord




# Load JSON files
n3_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n3") if f.endswith(".json")]
n3_vocabulary_files.sort()

n2_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n2") if f.endswith(".json")]
n2_vocabulary_files.sort()

def fetch_and_show_word():
    if st.query_params["word"] in n3_vocabulary_files:
        with open("resources/words/n3/" + st.query_params["word"] + ".json", "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
    elif st.query_params["word"] in n2_vocabulary_files:
        with open("resources/words/n2/" + st.query_params["word"] + ".json", "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
    if 'w' in locals():
        w.show_in_streamlit(st)


if "word" in st.query_params:
    fetch_and_show_word()
else:
    st.markdown("# JLPT Vocabularies")
    with st.expander("N3 Vocabularies"):
        with st.container(horizontal=True):
            for file in n3_vocabulary_files:
                st.button(file, on_click=lambda f=file: st.query_params.update({"word": f}), key=file)

    with st.expander("N2 Vocabularies"):
        with st.container(horizontal=True):
            for file in n2_vocabulary_files:
                st.button(file, on_click=lambda f=file: st.query_params.update({"word": f}), key=file)


