import os
import time

import streamlit as st
from dotenv import load_dotenv
from streamlit_cookies_controller import CookieController
from supabase import Client, create_client

from src.word.JPWord import LANGUAGES_ABBR

controller = CookieController()


auth = controller.get("auth")
if auth:
    st.session_state["auth"] = auth


load_dotenv()

url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)


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
            if response.user is not None and response.session is not None:
                controller.set(
                    name="auth",
                    value={
                        **response.user.user_metadata,
                        "id": response.user.id,
                        "email": response.user.email,
                        "access_token": response.session.access_token,
                        "refresh_token": response.session.refresh_token,
                    },
                )
                st.session_state["auth"] = {
                    **response.user.user_metadata,
                    "id": response.user.id,
                    "email": response.user.email,
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                }
                time.sleep(1)
                st.snow()
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


if auth is None:
    st.button("Login", on_click=login_modal, width="stretch", icon="🔐")
    st.button("Sign Up", on_click=signup_modal, width="stretch", icon="🆕")
else:
    st.set_page_config(page_title=f"{auth['username']} Profile", page_icon="👤")
    if auth.get("access_token") and auth.get("refresh_token"):
        supabase.auth.set_session(access_token=auth["access_token"], refresh_token=auth["refresh_token"])
    st.markdown(f"### Welcome, {auth['username']}!")
    with st.expander("User Details", expanded=True, icon="ℹ️"):
        st.text_input("Email", value=auth["email"], disabled=True)
        st.text_input("Username", value=auth["username"], key="username")
        st.selectbox(
            "Current JLPT Level",
            ["N5", "N4", "N3", "N2", "N1"],
            index=["N5", "N4", "N3", "N2", "N1"].index(auth.get("jlpt_level", "N5")),
            key="jlpt_level",
        )
        st.multiselect(
            "Preferred Languages",
            list(LANGUAGES_ABBR.keys()),
            default=auth.get("preferred_languages", ["English"]),
            key="preferred_languages",
        )
        if st.button("Update Profile", width="stretch"):
            try:
                updates = {
                    "username": st.session_state["username"],
                    "jlpt_level": st.session_state["jlpt_level"],
                    "preferred_languages": st.session_state["preferred_languages"],
                }
                response = supabase.auth.update_user({"data": updates})
                if response.user is not None:
                    controller.set(
                        name="auth",
                        value={
                            **response.user.user_metadata,
                            "id": response.user.id,
                            "email": response.user.email,
                            "access_token": auth.get("access_token"),
                            "refresh_token": auth.get("refresh_token"),
                        },
                    )
                    st.session_state["auth"] = {
                        **response.user.user_metadata,
                        "id": response.user.id,
                        "email": response.user.email,
                        "access_token": auth.get("access_token"),
                        "refresh_token": auth.get("refresh_token"),
                    }
                    time.sleep(1)
                    st.success("Profile updated successfully!")
                    st.rerun()
                else:
                    st.error("Update failed. Please try again.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    # if st.sidebar.button("Logout", width="stretch"):
    #     supabase.auth.sign_out()
    #     controller.remove("auth")
    #     if "auth" in st.session_state:
    #         del st.session_state["auth"]
    #     time.sleep(1)
    #     st.rerun()
