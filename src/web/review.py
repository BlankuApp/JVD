from datetime import datetime, timezone

import streamlit as st

from src.db.db_word import update_user_word_card, get_due_card
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


def reset_review_session():
    del st.session_state.review_state
    del st.session_state.current_card
    if "your_answer" in st.session_state:
        del st.session_state["your_answer"]
    st.rerun()


if "review_state" not in st.session_state:
    card = get_due_card(auth)
    if len(card) == 0:
        st.success("You have completed all reviews for now! Great job! 🎉")
        st.stop()
    st.session_state.current_card = card[0]
    st.toast("Generating the question...", icon="⏳")
    card: JPWordCard = JPWordCard(
        word=card[0]["key"],
        card_id=card[0]["id"],
        state=card[0]["state"],
        step=card[0]["step"],
        stability=card[0]["stability"],
        difficulty=card[0]["difficulty"],
        due=datetime.strptime(card[0]["due"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
        if card[0]["due"]
        else None,
        last_review=datetime.strptime(card[0]["last_review"], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
        if card[0]["last_review"]
        else None,
    )
    question = card.generate_reverse_translation_question(
        jlpt_level=auth["jlpt_level"], target_languages=auth["preferred_languages"]
    )

    st.session_state.update(
        {
            "review_state": "question",
            "current_card": {
                **st.session_state.current_card,
                "jpword": card,
                "qa": question,
            },
            "your_answer": "",
            "has_ai_review": False,
        }
    )

if st.session_state.review_state == "question":
    question = st.session_state.current_card["qa"]
    st.markdown("Question:")
    st.markdown(f"<p style='text-align: center; font-size: 24px;'>{question.question}</p>", unsafe_allow_html=True)
    st.markdown("Your Answer:")
    st.text_input(
        "Type your answer here", key="your_answer", label_visibility="collapsed", placeholder="Type your answer here"
    )
    with st.expander("Hint", expanded=False):
        st.markdown("- " + question.hints.replace(",", "\n- "))
    if st.button("Check Answer", type="primary", width="stretch"):
        st.session_state.review_state = "answer"
        st.rerun()

if st.session_state.review_state == "answer":
    question = st.session_state.current_card["qa"]
    if not st.session_state["has_ai_review"]:
        st.toast("Reviewing your answer with AI. Please wait ...", icon="⏳")
        review = st.session_state.current_card["jpword"].review_reverse_translation_question(
            user_answer=st.session_state["your_answer"],
            target_languages=auth["preferred_languages"],
        )
        st.session_state["ai_review"] = review
        st.session_state["has_ai_review"] = True
    st.markdown("Question:")
    st.markdown(f"<p style='text-align: center; font-size: 24px;'>{question.question}</p>", unsafe_allow_html=True)
    st.text_input("Type your answer here", key="your_answer", placeholder="Type your answer here")
    with st.expander("Hint", expanded=False):
        st.markdown("- " + question.hints.replace(",", "\n- "))
    st.markdown("Correct Answer:")
    st.markdown(f"<p style='text-align: center; font-size: 24px;'>{question.answer}</p>", unsafe_allow_html=True)
    st.text_area("AI Review", height=400, max_chars=None, key="ai_review")
    diff = st.segmented_control(
        "Rating:",
        ["Again", "Hard", "Good", "Easy"],
        default="Good",
        key="review_difficulty",
        label_visibility="collapsed",
        width="stretch",
    )
    if st.button("Submit Answer", type="primary", width="stretch"):
        jp_word_card: JPWordCard = st.session_state.current_card["jpword"]
        rating = RATING_DICT[st.session_state["review_difficulty"]]
        sch = Scheduler(enable_fuzzing=False)
        review_datetime = datetime.now(timezone.utc)
        jp_word_card, review_log = sch.review_card(jp_word_card, rating, review_datetime)
        success, msg = update_user_word_card(
            auth,
            word=jp_word_card.word,
            state=jp_word_card.state,
            step=jp_word_card.step,
            stability=jp_word_card.stability,
            difficulty=jp_word_card.difficulty,
            due=jp_word_card.due.isoformat() if jp_word_card.due else None,
            last_review=review_datetime.isoformat(),
        )
        st.session_state["due_review_count"] = max(st.session_state.get("due_review_count", 0) - 1, 0)
        st.toast(msg, icon="✅" if success else "❌")
        reset_review_session()
