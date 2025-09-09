import streamlit as st

st.title("Japanese Video Dictionary")
st.markdown("Welcome to the Japanese Video Dictionary! Use the sidebar to navigate through different sections.")
st.markdown(
    "Check out my [YouTube channel](https://www.youtube.com/@JapaneseVideoDictionary) for more Japanese learning content!"
)

if st.button("Start Learning", width="stretch", type="primary"):
    st.switch_page("src/web/v.py")
