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
            "review_state": "question",  # other states: "answer", "finished"
            "current_card": {
                **st.session_state.current_card,
                "jpword": card,
                "qa": question,
            },
        }
    )

if st.session_state.review_state == "question":
    question = st.session_state.current_card["qa"]
    st.markdown("Question:")
    st.title(f"{question.question}")
    st.markdown("Your Answer:")
    # st.markdown(f"### Question:\n{question.question}\n### Your Answer:")
    user_answer = st.text_input("Your Answer:", value="", key="your_answer", label_visibility="collapsed")
    with st.expander("Hint"):
        st.markdown("- " + question.hints.replace(",", "\n- "))
    if st.button("Check Answer", type="primary", width="stretch"):
        st.session_state.review_state = "answer"
        st.rerun()

if st.session_state.review_state == "answer":
    question = st.session_state.current_card["qa"]
    st.markdown("Question:")
    st.title(f"{question.question}")
    st.markdown("Your Answer:")
    # st.markdown(f"### Question:\n{question.question}\n### Your Answer:")
    st.text_input(
        "Your Answer:",
        value=st.session_state.get("your_answer", ""),
        key="your_answer",
        disabled=True,
        label_visibility="collapsed",
    )
    with st.expander("Hint"):
        st.markdown("- " + question.hints.replace(",", "\n- "))
    st.markdown("Correct Answer:")
    st.title(f"{question.answer}")
    # st.markdown(f"### Correct Answer:\n{question.answer}")
    st.segmented_control(
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
        st.toast(msg, icon="✅" if success else "❌")
        reset_review_session()


# if st.button("Reset Review Session", width="stretch"):
#     reset_review_session()
