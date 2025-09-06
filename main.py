import os
import time

import streamlit as st
from dotenv import load_dotenv
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer
from supabase import Client, create_client

load_dotenv()

controller = CookieController()
RemoveEmptyElementContainer()

url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)

auth = controller.get("auth")
if auth:
    st.session_state["auth"] = auth

main_page = st.Page("src/web/main_page.py", title="Home", icon="🏠")
jlpt_vocabularies = st.Page("src/web/v.py", title="JLPT Vocabularies", icon="📚")
if auth:
    user_auth = st.Page("src/web/user.py", title=f"{auth['username']} Profile", icon="👤")
    logout_btn = st.sidebar.button("Logout", width="stretch")
    if logout_btn:
        supabase.auth.sign_out()
        controller.remove("auth")
        if "auth" in st.session_state:
            del st.session_state["auth"]
        time.sleep(1)
        st.rerun()
else:
    user_auth = st.Page("src/web/user.py", title="Login", icon="🔐")


pages = [main_page, jlpt_vocabularies, user_auth]

app = st.navigation(pages=pages, expanded=True)
app.run()
