import streamlit as st
import os

# Load JSON files
n3_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n3") if f.endswith(".json")]
n3_vocabulary_files.sort()

n2_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n2") if f.endswith(".json")]
n2_vocabulary_files.sort()

st.title("Japanese Video Dictionary")
st.markdown("Welcome to the Japanese Video Dictionary! Use the sidebar to navigate through different sections.")
st.markdown(
    "Check out my [YouTube channel](https://www.youtube.com/@JapaneseVideoDictionary) for more Japanese learning content!"
)

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
