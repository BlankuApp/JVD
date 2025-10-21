"""
Japanese vocabulary review page using FSRS spaced repetition.

This page handles the main review workflow including question generation,
answer submission, AI grading, and scheduling updates.
"""

from datetime import datetime, timezone
from typing import Optional

import streamlit as st

from src.db.db_word import update_user_word_card
from src.pyfsrs.review_log import Rating
from src.pyfsrs.scheduler import Scheduler
from src.pyfsrs.question_service import load_word_json
from src.utils import create_html_with_ruby
from src.web.review_state import ReviewStateManager
from src.web.review_ui import (
    render_question_display,
    render_context_question,
    render_correct_answer,
    render_user_answer,
    render_hints_popover,
    render_rating_form,
)
from src.web.review_processing import (
    AnswerValidator,
    AudioProcessor,
    AIReviewGenerator,
    AUDIO_SAMPLE_RATE,
)

# Rating mapping from UI to FSRS enum
RATING_DICT = {
    "🔄 Again": Rating.Again,
    "😅 Hard": Rating.Hard,
    "😊 Good": Rating.Good,
    "🏆 Easy": Rating.Easy,
}

# Initialize state manager and auth
state_manager = ReviewStateManager()
auth: Optional[dict] = st.session_state.get("auth", None)

if not auth:
    st.warning("You need to be logged in to access the review page.")
    st.stop()

# Initialize review session if needed
if state_manager.get_current_state() is None:
    try:
        success = state_manager.initialize_review(auth)
        if not success:
            st.success("You have completed all reviews for now! Great job! 🎉")
            st.stop()
    except RuntimeError as e:
        st.error(f"❌ Failed to load review: {str(e)}")
        st.stop()

# QUESTION STATE: Display question and collect answer
if state_manager.get_current_state() == state_manager.STATES["question"]:
    current_card = state_manager.get_current_card()
    if not current_card or not current_card.get("qa"):
        st.error("❌ Failed to load question data")
        st.stop()

    question = current_card["qa"]
    assert question is not None  # Type checker hint

    # Display question
    render_question_display(question.question)

    # Callback to transcribe audio and update answer field
    def on_audio_change():
        """Transcribe audio input and automatically populate the answer field."""
        audio_data = st.session_state.get("audio_widget")
        if audio_data is not None:
            try:
                transcribed_text = AudioProcessor.transcribe_audio(audio_data)
                st.session_state["your_answer"] = transcribed_text
                st.toast("✅ Audio transcribed successfully!", icon="🎤")
            except RuntimeError as e:
                st.error(f"❌ Transcription failed: {str(e)}")

    # Audio input outside form (Streamlit only allows callbacks on form_submit_button inside forms)
    audio_input = st.audio_input(
        "🎤 record your answer:",
        sample_rate=AUDIO_SAMPLE_RATE,
        key="audio_widget",
        on_change=on_audio_change,
        help="Record your answer in Japanese",
        label_visibility="collapsed",
    )

    # Answer submission form
    with st.form("review_form", border=False):
        text_input = st.text_input(
            "Japanese Translation:",
            key="your_answer",
            label_visibility="collapsed",
            placeholder="日本語で答えてください...",
            autocomplete="off",
            help="Type your Japanese translation here",
        )

        # Button layout
        col1, col2 = st.columns([1, 1])
        with col1:
            render_hints_popover(question.hints)

        with col2:
            submitted = st.form_submit_button("✅ Check Answer", type="primary", use_container_width=True)

    # Handle form submission
    if submitted:
        is_valid, error_msg = AnswerValidator.validate_answer_input(text_input)
        if not is_valid:
            assert error_msg is not None  # Type checker hint
            AnswerValidator.display_validation_error(error_msg)
            st.stop()

        state_manager.transition_to_answer()

# ANSWER STATE: Display feedback and collect rating
if state_manager.get_current_state() == state_manager.STATES["answer"]:
    current_card = state_manager.get_current_card()
    if not current_card or not current_card.get("qa") or not current_card.get("card"):
        st.error("❌ Failed to load card data")
        st.stop()

    question = current_card["qa"]
    card = current_card["card"]
    word = current_card["key"]
    assert question is not None  # Type checker hint

    # Show original question for context
    render_context_question(question.question)

    # Process answer if not already done
    if not state_manager.has_ai_review():
        # Generate AI review
        try:
            final_answer = state_manager.get_answer()
            if not final_answer:
                st.error("❌ No answer to review")
                st.stop()

            review = AIReviewGenerator.generate_review(
                word=word,
                correct_answer=question.answer,
                source_question=question.question,
                user_answer=final_answer,
                target_languages=auth.get("preferred_languages", ["English"]),
            )
            state_manager.set_ai_review(review)
        except RuntimeError as e:
            st.error(f"❌ {str(e)}")
            st.stop()

    # Display answer review
    ruby = create_html_with_ruby(question.answer, font_size="1.5rem", rt_font_size="1.1rem")
    render_correct_answer(ruby)

    user_answer = state_manager.get_answer()
    render_user_answer(user_answer)

    # AI Review section
    with st.container(border=True):
        st.markdown(state_manager.get_ai_review())

    # Rating form
    selected_rating, rating_submitted = render_rating_form()

    if rating_submitted:
        state_manager.transition_to_submitting()

    # Display related video if available
    try:
        word_json = load_word_json(word)
        youtube_link = word_json.get("youtube_link")
        if youtube_link:
            st.markdown("### 🎥 Related Video")
            with st.container(border=False):
                st.video(youtube_link)
                st.caption("Watch this video to learn more about this word!")
    except Exception:
        # Ignore if word JSON not found or no video
        pass

# SUBMITTING STATE: Save review and load next card
if state_manager.get_current_state() == state_manager.STATES["submitting"]:
    try:
        with st.spinner("Submitting your answer...", show_time=True):
            current_card = state_manager.get_current_card()
            if not current_card or not current_card.get("card"):
                raise RuntimeError("Failed to load card data for submission")

            # Get rating and card
            rating = RATING_DICT.get(st.session_state.get("review_difficulty", "😊 Good"))
            if rating is None:
                raise RuntimeError("Invalid rating selected")

            card = current_card["card"]
            word = current_card["key"]
            review_datetime = datetime.now(timezone.utc)

            # Ensure card is not None (already checked above but helps type checker)
            assert card is not None

            # Update FSRS parameters using scheduler
            scheduler = Scheduler(enable_fuzzing=True, desired_retention=0.95)
            reviewed_card, review_log = scheduler.review_card(card, rating, review_datetime)

            # Persist to database
            success, msg = update_user_word_card(
                auth,
                word=word,
                state=str(int(reviewed_card.state)),
                step=reviewed_card.step,
                stability=reviewed_card.stability,
                difficulty=reviewed_card.difficulty,
                due=reviewed_card.due.isoformat() if reviewed_card.due else None,
                last_review=review_datetime.isoformat(),
            )

            # Update review count
            remaining = max(st.session_state.get("due_review_count", 0) - 1, 0)
            st.session_state["due_review_count"] = remaining

            # Show result message
            if success:
                if remaining > 0:
                    st.toast(f"✅ {msg} • {remaining} cards remaining", icon="🎯")
                else:
                    st.toast("🎉 Review session completed! Great work!", icon="🏆")
            else:
                st.error(f"❌ Failed to save: {msg}")

        # Reset and load next card
        state_manager.reset()

    except RuntimeError as e:
        st.error(f"❌ Error during submission: {str(e)}")
        st.stop()
