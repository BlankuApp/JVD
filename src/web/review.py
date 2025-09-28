from datetime import datetime, timezone

import streamlit as st

from src.db.db_word import update_user_word_card, get_due_card
from src.pyfsrs.card import JPWordCard
from src.pyfsrs.review_log import Rating
from src.pyfsrs.scheduler import Scheduler
from src.utils import create_html_with_ruby

RATING_DICT = {
    "🔄 Again": Rating.Again,
    "😅 Hard": Rating.Hard,
    "😊 Good": Rating.Good,
    "🏆 Easy": Rating.Easy,
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
    with st.spinner("Generating the question...", show_time=True):
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
    with st.form("review_form", border=False):
        question = st.session_state.current_card["qa"]
        st.markdown(f"<p style='text-align: center; font-size: 24px;'>{question.question}</p>", unsafe_allow_html=True)
        st.text_input(
            "Japanese Translation:",
            key="your_answer",
            label_visibility="collapsed",
            placeholder="Type your answer here",
            autocomplete="off",
        )
        col1, col2 = st.columns([0.5, 0.5])
        with col2:
            with st.popover("Hint", icon="💡", use_container_width=True):
                st.markdown("- " + question.hints.replace(",", "\n- "))
        with col1:
            submitted = st.form_submit_button("Check Answer", type="primary", use_container_width=True)
    if submitted:
        st.session_state.review_state = "answer"
        st.rerun()

if st.session_state.review_state == "answer":
    question = st.session_state.current_card["qa"]
    st.markdown(f"<p style='text-align: center; font-size: 24px;'>{question.question}</p>", unsafe_allow_html=True)
    if not st.session_state["has_ai_review"]:
        with st.spinner("Reviewing your answer with AI. Please wait ...", show_time=True):
            review = st.session_state.current_card["jpword"].review_reverse_translation_question(
                user_answer=st.session_state["your_answer"],
                target_languages=auth["preferred_languages"],
            )
        st.session_state["ai_review"] = review
        st.session_state["has_ai_review"] = True
    with st.container():
        ruby = create_html_with_ruby(question.answer, font_size="2rem", rt_font_size="1.1rem")
        st.markdown(
            f"<p style='text-align: center; font-weight: bold;'>{ruby}</p>",
            unsafe_allow_html=True,
        )
        if "your_answer" in st.session_state:
            st.markdown(f"**Your Answer:** {st.session_state['your_answer']}")
        st.markdown(st.session_state["ai_review"])
    with st.form("rating_form", border=False):
        diff = st.segmented_control(
            "Rating:",
            ["🔄 Again", "😅 Hard", "😊 Good", "🏆 Easy"],
            default="😊 Good",
            key="review_difficulty",
            label_visibility="collapsed",
            width="stretch",
        )
        jp_word_card: JPWordCard = st.session_state.current_card["jpword"]
        submitted = st.form_submit_button("Submit Answer", type="primary", use_container_width=True)
        if submitted:
            st.session_state["review_state"] = "submitting"
    youtube_link = jp_word_card.json_data["youtube_link"]
    if youtube_link:
        st.video(youtube_link)

if st.session_state.review_state == "submitting":
    with st.spinner("Submitting your answer...", show_time=True):
        rating = RATING_DICT[st.session_state["review_difficulty"]]
        sch = Scheduler(enable_fuzzing=True, desired_retention=0.95)
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
