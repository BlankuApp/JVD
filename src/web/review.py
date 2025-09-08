import streamlit as st
import time
from src.pyfsrs.card import JPWordCard


print(f"Review page loaded at {time.strftime('%X')}")


def on_click():
    st.session_state["user_word_cards"].pop(0)


def get_question():
    if len(st.session_state["user_word_cards"]) == 0:
        return None
    card_json = st.session_state["user_word_cards"][0]
    card: JPWordCard = JPWordCard(
        word=card_json["key"],
        card_id=card_json["id"],
        state=card_json["state"],
        step=1,
        stability=card_json["stability"],
        difficulty=card_json["difficulty"],
        due=card_json["due"],
        last_review=card_json["last_review"],
    )
    question = card.generate_reverse_translation_question(jlpt_level="N3", target_language="English")
    st.session_state["question"] = question.question
    st.session_state["answer"] = question.answer
    st.session_state["hints"] = question.hints


auth = st.session_state.get("auth", None)

if not auth:
    st.warning("You need to be logged in to access the review page.")
    st.stop()


if not st.session_state.get("user_word_cards", []):
    st.write("You have no cards in your review list. Please add some words to your list first.")
    st.stop()

get_question()
st.text_input("Question:", value="", key="question", disabled=True)
st.text_input("Your Answer:", value="", key="answer")
with st.expander("Hint"):
    st.text_area("hints", label_visibility="collapsed", key="hints", disabled=True)
b = st.button("Check Answer", type="primary", on_click=on_click)
