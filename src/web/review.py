import time
from datetime import datetime, timedelta, timezone

import streamlit as st

from src.db.db_word import update_user_word_card
from src.pyfsrs.card import JPWordCard
from src.pyfsrs.review_log import Rating
from src.pyfsrs.scheduler import Scheduler

RATING_DICT = {
    "Again": Rating.Again,
    "Hard": Rating.Hard,
    "Good": Rating.Good,
    "Easy": Rating.Easy,
}

auth = st.session_state.get("auth", None)

if not auth:
    st.warning("You need to be logged in to access the review page.")
    st.stop()

print(f"Review page loaded at {time.strftime('%X')}")


def on_click():
    st.session_state.review_show_answer = True
    # st.session_state["user_word_cards"].pop(0)


def get_question():
    if len(st.session_state["user_word_cards"]) == 0:
        return None
    card_json = st.session_state["user_word_cards"][0]
    card: JPWordCard = JPWordCard(
        word=card_json["key"],
        card_id=card_json["id"],
        state=card_json["state"],
        step=card_json["step"],
        stability=card_json["stability"],
        difficulty=card_json["difficulty"],
        due=card_json["due"],
        last_review=card_json["last_review"],
    )
    question = card.generate_reverse_translation_question(jlpt_level="N3", target_language="English")
    st.session_state.review_show_answer = False
    st.session_state.question = question.question
    st.session_state.answer = question.answer
    st.session_state.hints = "- " + question.hints.replace(",", "\n- ")


if not st.session_state.get("user_word_cards", []):
    st.write("You have no cards in your review list. Please add some words to your list first.")
    st.stop()

if st.session_state.get("question", None) is None:
    get_question()
st.text_input("Question:", value="", key="question", disabled=True)
st.text_input("Your Answer:", value="", key="your_answer")
with st.expander("Hint"):
    st.markdown(st.session_state.get("hints", "No hints available."))

if st.session_state.get("review_show_answer", False):
    st.text_input("Correct Answer:", value=st.session_state.answer)
    st.segmented_control(
        "Rating:",
        ["Again", "Hard", "Good", "Easy"],
        default="Good",
        key="review_difficulty",
        label_visibility="collapsed",
        width="stretch",
    )
    if st.button("Submit Answer", type="primary", width="stretch"):
        # card_json = st.session_state["user_word_cards"].pop(0)
        card_json = st.session_state["user_word_cards"][0]
        card: JPWordCard = JPWordCard(
            word=card_json["key"],
            card_id=card_json["id"],
            state=card_json["state"],
            step=card_json["step"],
            stability=card_json["stability"],
            difficulty=card_json["difficulty"],
            due=datetime.strptime(card_json["due"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
            if card_json["due"]
            else None,
            last_review=datetime.strptime(card_json["last_review"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
            if card_json["last_review"]
            else None,
        )

        rating = RATING_DICT[st.session_state["review_difficulty"]]
        sch = Scheduler(enable_fuzzing=False)
        review_datetime = datetime.now(timezone.utc)
        card, review_log = sch.review_card(card, rating, review_datetime)
        success, msg = update_user_word_card(
            auth,
            word=card.word,
            state=card.state,
            step=card.step,
            stability=card.stability,
            difficulty=card.difficulty,
            due=card.due.isoformat() if card.due else None,
            last_review=review_datetime.isoformat(),
        )
        st.toast(msg, icon="✅" if success else "❌")
        if True:
            st.session_state["user_word_cards"].pop(0)
            if len(st.session_state["user_word_cards"]) == 0:
                st.success("You have completed all reviews for now! Great job! 🎉")
                st.stop()
            get_question()
            st.rerun()

else:
    st.button("Check Answer", type="primary", on_click=on_click, width="stretch")
