"""
Answer processing and validation logic for the review workflow.

This module handles audio transcription, answer validation, and AI review generation.
"""

from io import BytesIO
from typing import Tuple, Optional
import streamlit as st
from src import get_openai_client


# Configuration constants for validation
AUDIO_SIZE_WARNING_KB = 200  # Show warning at this size
AUDIO_SIZE_LIMIT_KB = 1000  # Hard limit for audio file size
AUDIO_SAMPLE_RATE = 8000  # Sample rate for audio input


class AnswerValidator:
    """Validates user answers (text or audio)."""

    @staticmethod
    def validate_answer_input(text_input: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the user provided an answer.

        Args:
            text_input: Text answer from user (may include transcribed audio)

        Returns:
            Tuple of (is_valid, error_message). error_message is None if valid.
        """
        text_provided = text_input and text_input.strip() != ""

        if not text_provided:
            return False, "Please provide an answer."

        return True, None

    @staticmethod
    def validate_audio_size(audio_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate audio file size.

        Args:
            audio_bytes: Audio data bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        audio_size_kb = len(audio_bytes) / 1024

        if audio_size_kb > AUDIO_SIZE_LIMIT_KB:
            return (
                False,
                f"Your audio file is {audio_size_kb:.2f}KB, which exceeds the limit of {AUDIO_SIZE_LIMIT_KB}KB. "
                "Please record a shorter answer.",
            )

        if audio_size_kb > AUDIO_SIZE_WARNING_KB:
            st.warning(
                f"⚠️ Your audio file is {audio_size_kb:.2f}KB. "
                f"It's recommended to keep files under {AUDIO_SIZE_WARNING_KB}KB for faster processing."
            )

        return True, None

    @staticmethod
    def display_validation_error(error_message: str) -> None:
        """Display validation error to user."""
        st.warning(error_message)


class AudioProcessor:
    """Handles audio transcription and processing."""

    @staticmethod
    def transcribe_audio(audio_input: BytesIO, language: str = "ja") -> str:
        """
        Transcribe audio input to text using OpenAI Whisper.

        Args:
            audio_input: Audio input as BytesIO object
            language: Language code for transcription (default: "ja" for Japanese)

        Returns:
            Transcribed text

        Raises:
            RuntimeError: If transcription fails
        """
        # Validate audio size
        audio_bytes = audio_input.getvalue()
        is_valid, error_msg = AnswerValidator.validate_audio_size(audio_bytes)

        if not is_valid:
            raise RuntimeError(error_msg)

        try:
            with st.spinner("🤖 Transcribing your voice answer... Please wait", show_time=True):
                openai_client = get_openai_client()

                # Prepare audio buffer with filename for Whisper
                audio_buffer = BytesIO(audio_bytes)
                audio_buffer.name = "audio.wav"

                # Call Whisper transcription
                audio_response = openai_client.audio.transcriptions.create(
                    file=audio_buffer,
                    model="gpt-4o-mini-transcribe",
                    response_format="text",
                    language=language,
                )

                transcribed_text = audio_response

                if not transcribed_text:
                    raise RuntimeError("Transcription returned empty result")

                return transcribed_text

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Audio transcription failed: {str(e)}") from e

class AIReviewGenerator:
    """Handles AI review generation for answers."""

    @staticmethod
    def generate_review(
        jpword_card,
        user_answer: str,
        target_languages: list[str],
    ) -> str:
        """
        Generate AI review for the user's answer.

        Args:
            jpword_card: JPWordCard object with question data
            user_answer: User's answer to review
            target_languages: Target languages for review output

        Returns:
            AI review as markdown-formatted string

        Raises:
            RuntimeError: If review generation fails
        """
        try:
            with st.spinner("🤖 AI is reviewing your answer... Please wait", show_time=True):
                review = jpword_card.review_reverse_translation_question(
                    user_answer=user_answer,
                    target_languages=target_languages,
                )

                if not review:
                    raise RuntimeError("Review generation returned empty result")

                return review

        except Exception as e:
            raise RuntimeError(f"Failed to generate AI review: {str(e)}") from e
