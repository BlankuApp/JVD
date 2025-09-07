import os
import time

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)

auth = st.session_state.get("auth", None)

main_page = st.Page("src/web/main_page.py", title="Home", icon="🏠")
jlpt_vocabularies = st.Page("src/web/v.py", title="JLPT Vocabularies", icon="📚")
review_page = st.Page("src/web/review.py", title="Review", icon="✏️")
if auth:
    user_auth = st.Page("src/web/user.py", title=f"{auth['username']} Profile", icon="👤")
    logout_btn = st.sidebar.button("Logout", width="stretch")
    if logout_btn:
        supabase.auth.sign_out()
        if "auth" in st.session_state:
            del st.session_state["auth"]
        time.sleep(1)
        st.rerun()
else:
    user_auth = st.Page("src/web/user.py", title="Login", icon="🔐")


pages = [main_page, jlpt_vocabularies, review_page, user_auth]
app = st.navigation(pages=pages, expanded=True)
st.sidebar.write(st.session_state)
app.run()
