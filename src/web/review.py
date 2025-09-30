from datetime import datetime, timezone

import streamlit as st

from src.db.db_word import get_due_card, update_user_word_card
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
    question = st.session_state.current_card["qa"]

    # Enhanced question display with better visual hierarchy
    with st.container(border=False):
        st.markdown("📝 Translate to Japanese")
        st.markdown(
            f"<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); "
            f"padding: 1rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 1rem;'>"
            f"<p style='text-align: center; font-size: 26px; color: white; margin: 0; "
            f"text-shadow: 1px 1px 2px rgba(0,0,0,0.3); line-height: 1.4;'>{question.question}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with st.form("review_form", border=False):
        answer_input = st.text_input(
            "Japanese Translation:",
            key="your_answer",
            label_visibility="collapsed",
            placeholder="日本語で答えてください...",
            autocomplete="off",
            help="Type your Japanese translation here",
        )

        # Enhanced button layout with better spacing
        col1, col2 = st.columns([1, 1])
        with col1:
            with st.popover("💡 Hint", use_container_width=True):
                st.markdown("**Helpful hints:**")
                hints_formatted = "• " + question.hints.replace(",", "\n• ")
                st.markdown(hints_formatted)

        with col2:
            submitted = st.form_submit_button("✅ Check Answer", type="primary", use_container_width=True)

    if submitted:
        st.session_state.review_state = "answer"
        st.rerun()

if st.session_state.review_state == "answer":
    question = st.session_state.current_card["qa"]

    # Show the original question again for context
    st.markdown("📖 Original Question")
    st.markdown(f"*{question.question}*")

    if not st.session_state["has_ai_review"]:
        with st.spinner("🤖 AI is reviewing your answer... Please wait", show_time=True):
            review = st.session_state.current_card["jpword"].review_reverse_translation_question(
                user_answer=st.session_state["your_answer"],
                target_languages=auth["preferred_languages"],
            )
        st.session_state["ai_review"] = review
        st.session_state["has_ai_review"] = True

    # Enhanced answer display section
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("✅ Correct Answer")
        ruby = create_html_with_ruby(question.answer, font_size="1.5rem", rt_font_size="1.1rem")
        st.markdown(
            f"<div style='background: #e8f5e8; padding: 0.5rem; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 1rem;'>"
            f"<div style='text-align: center;'>{ruby}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("📝 Your Answer")
        user_answer = st.session_state.get("your_answer", "")
        if user_answer.strip() == "":
            answer_display = "<em style='color: #6c757d;'>Skipped</em>"
            answer_style = "background: #f8f9fa; border-left: 5px solid #6c757d;"
        else:
            answer_display = user_answer
            answer_style = "background: #f8f9fa; border-left: 5px solid #007bff;"

        st.markdown(
            f"<div style='{answer_style} padding: 0.5rem; border-radius: 10px; margin-bottom: 1rem;'>"
            f"<div style='text-align: center; font-size: 1.5rem;'>{answer_display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # AI Review section with enhanced styling
    with st.container(border=True):
        st.markdown(st.session_state["ai_review"])

    # Enhanced rating form with better descriptions
    with st.form("rating_form", border=False):
        st.markdown("📊 How well did you know this word?")

        # Add descriptions for each rating
        rating_descriptions = {
            "🔄 Again": "I didn't know it at all",
            "😅 Hard": "I knew it but struggled",
            "😊 Good": "I knew it well",
            "🏆 Easy": "I knew it perfectly",
        }

        selected_rating = st.segmented_control(
            "Rating:",
            list(rating_descriptions.keys()),
            default="😊 Good",
            key="review_difficulty",
            label_visibility="collapsed",
            width="stretch",
        )

        jp_word_card: JPWordCard = st.session_state.current_card["jpword"]

        if st.form_submit_button("📚 Submit & Continue", type="primary", use_container_width=True):
            st.session_state["review_state"] = "submitting"

    # Enhanced YouTube video section
    youtube_link = jp_word_card.json_data.get("youtube_link")
    if youtube_link:
        st.markdown("### 🎥 Related Video")
        with st.container(border=False):
            st.video(youtube_link)
            st.caption("Watch this video to learn more about this word!")

if st.session_state.review_state == "submitting":
    with st.spinner("Submitting your answer...", show_time=True):
        rating = RATING_DICT[st.session_state["review_difficulty"]]
        sch = Scheduler(enable_fuzzing=True, desired_retention=0.95)
        review_datetime = datetime.now(timezone.utc)
        jp_word_card: JPWordCard = st.session_state.current_card["jpword"]
        jp_word_card, review_log = sch.review_card(jp_word_card, rating, review_datetime)

        success, msg = update_user_word_card(
            auth,
            word=jp_word_card.word,
            state=str(int(jp_word_card.state)),  # Convert State enum to string of integer value
            step=jp_word_card.step,
            stability=jp_word_card.stability,
            difficulty=jp_word_card.difficulty,
            due=jp_word_card.due.isoformat() if jp_word_card.due else None,
            last_review=review_datetime.isoformat(),
        )
        st.session_state["due_review_count"] = max(st.session_state.get("due_review_count", 0) - 1, 0)

        # Enhanced success message with progress
        if success:
            remaining = st.session_state.get("due_review_count", 0)
            if remaining > 0:
                st.toast(f"✅ {msg} • {remaining} cards remaining", icon="🎯")
            else:
                st.toast("🎉 Review session completed! Great work!", icon="🏆")
        else:
            st.toast(msg, icon="❌")

        reset_review_session()
