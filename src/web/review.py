from datetime import datetime, timezone
from io import BytesIO

import streamlit as st

from src import get_openai_client
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
        text_input = st.text_input(
            "Japanese Translation:",
            key="your_answer",
            label_visibility="collapsed",
            placeholder="日本語で答えてください...",
            autocomplete="off",
            help="Type your Japanese translation here",
        )

        audio_input = st.audio_input(
            "🎤 Or record your answer:",
            key="your_voice_answer",
            sample_rate=8000,
            help="Record your answer in Japanese (max 1000KB)",
        )
        # Enhanced button layout with better spacing
        col1, col2 = st.columns([1, 1])
        with col1:
            with st.popover("💡 Hint", use_container_width=True):
                st.markdown("**Helpful hints:**")
                hints = question.hints.split(",")
                for hint in hints:
                    st.markdown(f"- {hint.strip()}")

        with col2:
            submitted = st.form_submit_button("✅ Check Answer", type="primary", use_container_width=True)

    if submitted:
        if (not text_input or text_input.strip() == "") and (
            "your_voice_answer" not in st.session_state or st.session_state["your_voice_answer"] is None
        ):
            st.warning("Please provide an answer either by typing or recording your voice.")
            if "your_voice_answer" in st.session_state and st.session_state["your_voice_answer"] is not None:
                audio_bytes = st.session_state["your_voice_answer"].getvalue()
                audio_size = len(audio_bytes) / 1024
                st.info(f"Your audio file size: {audio_size:.2f}KB")
                if audio_size > 200:
                    st.warning("Your audio file is too large. Please keep it under 200KB.")
            st.stop()
        st.session_state.review_state = "answer"
        st.rerun()

if st.session_state.review_state == "answer":
    question = st.session_state.current_card["qa"]

    # Show the original question again for context
    # st.markdown("📖 Original Question")
    # st.markdown(f"*{question.question}*")
    st.markdown(
        f"<div style='background: #f8f9fa; padding: 0.5rem; border-radius: 10px; border-left: 5px solid #C4C4C4; margin-bottom: 0.5rem;'>"
        f"<div style='font-size: 0.9rem; color: #C4C4C4;'>📖 Original Question</div>    "
        f"<div style='text-align: center; font-size: 1.2rem;'>{question.question}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not st.session_state["has_ai_review"]:
        if "your_voice_answer" in st.session_state and st.session_state["your_voice_answer"] is not None:
            with st.spinner("🤖 Transcribing your voice answer... Please wait", show_time=True):
                openai = get_openai_client()
                audio_bytes = st.session_state["your_voice_answer"].getvalue()
                audio_size = len(audio_bytes) / 1024
                st.info(f"Your audio file size: {audio_size:.2f}KB")
                if audio_size > 1000:
                    st.warning("Your audio file is too large. Please keep it under 1000KB.")
                    st.stop()
                audio_buffer = BytesIO(audio_bytes)
                audio_buffer.name = "audio.wav"  # Whisper needs a filename to detect format

                audio_response = openai.audio.transcriptions.create(
                    file=audio_buffer, model="gpt-4o-mini-transcribe", response_format="text", language="ja"
                )
                st.session_state["your_answer"] = audio_response

        with st.spinner("🤖 AI is reviewing your answer... Please wait", show_time=True):
            review = st.session_state.current_card["jpword"].review_reverse_translation_question(
                user_answer=st.session_state["your_answer"],
                target_languages=auth["preferred_languages"],
            )
        st.session_state["ai_review"] = review
        st.session_state["has_ai_review"] = True

    # st.markdown("✅ Correct Answer")
    ruby = create_html_with_ruby(question.answer, font_size="1.5rem", rt_font_size="1.1rem")
    st.markdown(
        f"<div style='background: #e8f5e8; padding: 0.5rem; border-radius: 10px; border-left: 5px solid #28a745; margin-bottom: 0.5rem;'>"
        f"<div style='font-size: 0.9rem; color: #28a745;'>✅ Correct Answer</div>"
        f"<div style='text-align: center;'>{ruby}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # st.markdown("📝 Your Answer")
    user_answer = st.session_state.get("your_answer", "")
    st.markdown(
        f"<div style='background: #f8f9fa; border-left: 5px solid #007bff; padding: 0.5rem; border-radius: 10px; margin-bottom: 0.5rem;'>"
        f"<div style='font-size: 0.9rem; color: #007bff;'>📝 Your Answer</div>"
        f"<div style='text-align: center; font-size: 1.5rem;'>{user_answer}</div>"
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
        reviewed_card, review_log = sch.review_card(jp_word_card, rating, review_datetime)

        success, msg = update_user_word_card(
            auth,
            word=jp_word_card.word,
            state=str(int(reviewed_card.state)),  # Convert State enum to string of integer value
            step=reviewed_card.step,
            stability=reviewed_card.stability,
            difficulty=reviewed_card.difficulty,
            due=reviewed_card.due.isoformat() if reviewed_card.due else None,
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
