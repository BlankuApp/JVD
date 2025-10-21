"""
UI styling and rendering helpers for the review page.

This module provides reusable components for consistent styling and layout
management across the review workflow (question, answer, feedback sections).
"""

import streamlit as st
from enum import Enum


class SectionStyle(Enum):
    """Color schemes and styling for different section types."""

    QUESTION = {
        "bg_color": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "text_color": "white",
        "border_color": None,
        "icon": "📝",
        "title": "Translate to Japanese",
    }
    ANSWER_CORRECT = {
        "bg_color": "#e8f5e8",
        "text_color": "#28a745",
        "border_color": "#28a745",
        "icon": "✅",
        "title": "Correct Answer",
    }
    ANSWER_USER = {
        "bg_color": "#f8f9fa",
        "text_color": "#007bff",
        "border_color": "#007bff",
        "icon": "📝",
        "title": "Your Answer",
    }
    CONTEXT = {
        "bg_color": "#f8f9fa",
        "text_color": "#C4C4C4",
        "border_color": "#C4C4C4",
        "icon": "📖",
        "title": "Original Question",
    }


def render_styled_section(
    content: str,
    section_type: SectionStyle,
    font_size: str = "1.5rem",
    is_html: bool = False,
    container_border: bool = True,
) -> None:
    """
    Render a styled section with consistent formatting.

    Args:
        content: The content to display (text or HTML)
        section_type: The styling preset to use (SectionStyle enum)
        font_size: Font size for the main content
        is_html: Whether content is already HTML
        container_border: Whether to show container border
    """
    style = section_type.value

    if section_type == SectionStyle.QUESTION:
        # Special handling for gradient background question
        st.markdown(
            f"<div style='background: {style['bg_color']}; "
            f"padding: 1rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 1rem;'>"
            f"<p style='text-align: center; font-size: {font_size}; color: {style['text_color']}; margin: 0; "
            f"text-shadow: 1px 1px 2px rgba(0,0,0,0.3); line-height: 1.4;'>{content}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        # Standard bordered sections
        st.markdown(
            f"<div style='background: {style['bg_color']}; border-left: 5px solid {style['border_color']}; "
            f"padding: 0.5rem; border-radius: 10px; margin-bottom: 0.5rem;'>"
            f"<div style='font-size: 0.9rem; color: {style['text_color']};'>{style['icon']} {style['title']}</div>"
            f"<div style='text-align: center; font-size: {font_size};'>{content}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def render_question_display(question_text: str) -> None:
    """Render the question with enhanced visual hierarchy."""
    with st.container(border=False):
        st.markdown("📝 Translate to Japanese")
        render_styled_section(
            content=question_text,
            section_type=SectionStyle.QUESTION,
            font_size="26px",
        )


def render_context_question(question_text: str) -> None:
    """Render the original question as context reference."""
    render_styled_section(
        content=question_text,
        section_type=SectionStyle.CONTEXT,
        font_size="1.2rem",
    )


def render_correct_answer(ruby_html: str) -> None:
    """Render the correct answer with ruby text."""
    render_styled_section(
        content=ruby_html,
        section_type=SectionStyle.ANSWER_CORRECT,
        font_size="1.5rem",
        is_html=True,
    )


def render_user_answer(user_answer: str) -> None:
    """Render the user's submitted answer."""
    render_styled_section(
        content=user_answer,
        section_type=SectionStyle.ANSWER_USER,
        font_size="1.5rem",
    )


def render_hints_popover(hints: str, word: str) -> None:
    """Render hints in an accordion (expander)."""
    with st.expander("💡 Hint", expanded=False):
        st.markdown("**Helpful hints:**")
        hints_list = hints.split(",")
        for hint in hints_list:
            st.markdown(f"- {hint.strip()}")
        try:
            # open the json file
            with open(f"resources/words/{word}.json", "r", encoding="utf-8") as f:
                import json

                word_data = json.load(f)
            st.markdown(f"👀 Word starts with: **{word_data.get('reading')[0]}**")
        except Exception:
            pass
        try:
            st.image(f"resources/images/{word}.png", width="content")
        except Exception:
            pass


def render_rating_form() -> tuple[str, bool]:
    """
    Render the rating form and return selected rating and submission status.

    Returns:
        Tuple of (selected_rating, was_submitted)
    """
    rating_descriptions = {
        "🔄 Again": "I didn't know it at all",
        "😅 Hard": "I knew it but struggled",
        "😊 Good": "I knew it well",
        "🏆 Easy": "I knew it perfectly",
    }

    with st.form("rating_form", border=False):
        st.markdown("📊 How well did you know this word?")

        selected_rating = st.segmented_control(
            "Rating:",
            list(rating_descriptions.keys()),
            default="😊 Good",
            key="review_difficulty",
            label_visibility="collapsed",
            width="stretch",
        )

        submitted = st.form_submit_button("📚 Submit & Continue", type="primary", use_container_width=True)

    return selected_rating, submitted
