import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client
import os
import time
from streamlit_cookies_controller import CookieController, RemoveEmptyElementContainer
from src.word.JPWord import LANGUAGES_ABBR

RemoveEmptyElementContainer()

load_dotenv()

url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)

controller = CookieController()
if controller.get("auth"):
    st.session_state["auth"] = controller.get("auth")


@st.dialog(title="Login")
def login_modal():
    st.text_input("Email", key="email")
    st.text_input("Password", type="password", key="password")
    if st.button("Login"):
        try:
            response = supabase.auth.sign_in_with_password(
                {
                    "email": st.session_state["email"],
                    "password": st.session_state["password"],
                }
            )
            if response.user is not None:
                controller.set(
                    name="auth",
                    value={**response.user.user_metadata, "id": response.user.id, "email": response.user.email},
                )
                st.session_state["auth"] = {
                    **response.user.user_metadata,
                    "id": response.user.id,
                    "email": response.user.email,
                }
                time.sleep(1)
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")
        except Exception as e:
            st.error(f"An error occurred: {e}")


@st.dialog(title="Sign Up")
def signup_modal():
    st.text_input("Username", key="signup_name")
    st.text_input("Email", key="signup_email")
    st.text_input("Password", type="password", key="signup_password")
    st.selectbox("Current JLPT Level", ["N5", "N4", "N3", "N2", "N1"], key="signup_jlpt_level")
    st.multiselect("Preferred Languages", list(LANGUAGES_ABBR.keys()), key="signup_language", default=["English"])
    if st.button("Sign Up"):
        try:
            response = supabase.auth.sign_up(
                {
                    "email": st.session_state["signup_email"],
                    "password": st.session_state["signup_password"],
                    "options": {
                        "data": {
                            "username": st.session_state["signup_name"],
                            "jlpt_level": st.session_state["signup_jlpt_level"],
                            "preferred_languages": st.session_state["signup_language"],
                        }
                    },
                }
            )
            if response.user is not None:
                st.success("Sign up successful! Please check your email to confirm your account.")
                time.sleep(10)
                st.rerun()
            else:
                st.error("Sign up failed. Please try again.")
        except Exception as e:
            st.error(f"An error occurred: {e}")


main_page = st.Page("src/web/main_page.py", title="Main Page", icon="🏠")
jlpt_vocabularies = st.Page("src/web/v.py", title="JLPT Vocabularies", icon="📚")
app = st.navigation(pages=[main_page, jlpt_vocabularies])

if not st.session_state.get("auth") or controller.get("auth") is None:
    st.sidebar.button("Login", on_click=login_modal, width="stretch", icon="🔐")
    st.sidebar.button("Sign Up", on_click=signup_modal, width="stretch", icon="🆕")
else:
    st.sidebar.success(f"Welcome {controller.get('auth')}!")
    if st.sidebar.button("Logout", width="stretch"):
        supabase.auth.sign_out()
        controller.remove("auth")
        if "auth" in st.session_state:
            del st.session_state["auth"]
        time.sleep(1)
        st.rerun()

app.run()
