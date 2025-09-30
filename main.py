import os
import time

import streamlit as st
from dotenv import load_dotenv
from streamlit_cookies_controller import CookieController
from supabase import Client, create_client

from src.db.db_word import get_due_cards_count

load_dotenv()

controller = CookieController()
url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)

auth = st.session_state.get("auth", None)
review_count = st.session_state.get("due_review_count", 0)
if auth:
    review_count = get_due_cards_count(auth)
    st.session_state["due_review_count"] = review_count
elif controller.get("jvd_token") is not None:
    try:
        response = supabase.auth.get_user(controller.get("jvd_token"))
        if response.user is not None:
            auth = {
                **response.user.user_metadata,
                "id": response.user.id,
                "email": response.user.email,
                "access_token": controller.get("jvd_token"),
            }
            st.session_state["auth"] = auth
            review_count = get_due_cards_count(auth)
            st.session_state["due_review_count"] = review_count
    except Exception as e:
        # st.error(f"An error occurred: {e}")
        controller.remove("jvd_token", secure=True, same_site="strict")

main_page = st.Page("src/web/main_page.py", title="Home", icon="🏠")
jlpt_vocabularies = st.Page("src/web/v.py", title="JLPT Vocabularies", icon="📚")
review_page = st.Page(
    "src/web/review.py", title="Review" if review_count == 0 else f"Review ({review_count})", icon="✏️"
)
fill_in_blank_page = st.Page("src/web/fill_in_the_blank.py", title="Fill in the Blank", icon="📝")
kanji_reading_page = st.Page("src/web/kanji_reading.py", title="Kanji Reading", icon="🈴")
if auth:
    user_auth = st.Page("src/web/user.py", title=f"{auth['username']} Profile", icon="👤")
    logout_btn = st.sidebar.button("Logout", width="stretch")
    if logout_btn:
        supabase.auth.sign_out()
        if "auth" in st.session_state:
            del st.session_state["auth"]
        if "due_review_count" in st.session_state:
            del st.session_state["due_review_count"]
        controller.remove("jvd_token", secure=True, same_site="strict")
        time.sleep(1)
        st.rerun()
else:
    user_auth = st.Page("src/web/user.py", title="Login", icon="🔐")

pages = [main_page, jlpt_vocabularies, review_page, fill_in_blank_page, kanji_reading_page, user_auth]
app = st.navigation(pages=pages, expanded=True)
app.run()
