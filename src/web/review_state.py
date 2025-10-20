"""
Review workflow state management.

This module handles all state transitions and data management for the review workflow,
including session state initialization, card hydration, and state cleanup.
"""

from datetime import datetime, timezone
from typing import TypedDict, Optional
import streamlit as st
from src.pyfsrs.card import JPWordCard, State
from src.db.db_word import get_due_card


class CardData(TypedDict):
    """Type definition for card database record."""

    id: int
    key: str
    state: str
    step: int
    stability: float
    difficulty: float
    due: Optional[str]
    last_review: Optional[str]


class CurrentCardState(TypedDict):
    """Type definition for current card session state."""

    id: int
    key: str
    state: str
    step: int
    stability: float
    difficulty: float
    due: Optional[str]
    last_review: Optional[str]
    jpword: Optional[JPWordCard]
    qa: Optional[dict]


class ReviewStateManager:
    """Manages the review workflow state and transitions."""

    # Review workflow states
    STATES = {
        "question": "question",
        "answer": "answer",
        "submitting": "submitting",
    }

    def __init__(self):
        """Initialize the state manager."""
        self._ensure_session_state_exists()

    @staticmethod
    def _ensure_session_state_exists() -> None:
        """Ensure required session state variables exist."""
        if "review_state" not in st.session_state:
            st.session_state.review_state = None
        if "current_card" not in st.session_state:
            st.session_state.current_card = None
        if "your_answer" not in st.session_state:
            st.session_state.your_answer = ""
        if "your_voice_answer" not in st.session_state:
            st.session_state.your_voice_answer = None
        if "ai_review" not in st.session_state:
            st.session_state.ai_review = ""
        if "has_ai_review" not in st.session_state:
            st.session_state.has_ai_review = False
        if "review_difficulty" not in st.session_state:
            st.session_state.review_difficulty = "😊 Good"

    @staticmethod
    def _parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """
        Parse ISO format datetime string to datetime object.

        Handles variable-length fractional seconds (e.g., 5 or 6 digits).

        Args:
            datetime_str: ISO format datetime string

        Returns:
            datetime object with UTC timezone, or None if input is None

        Raises:
            ValueError: If datetime string cannot be parsed
        """
        if not datetime_str:
            return None
        try:
            # Try standard fromisoformat first
            return datetime.fromisoformat(datetime_str).replace(tzinfo=timezone.utc)
        except ValueError:
            # Handle variable-length fractional seconds by normalizing to 6 digits
            try:
                if "." in datetime_str:
                    # Split into base and fractional parts
                    base, frac_and_tz = datetime_str.split(".", 1)

                    # Handle timezone info if present
                    tz_part = ""
                    if "+" in frac_and_tz:
                        frac, tz_part = frac_and_tz.split("+", 1)
                        tz_part = "+" + tz_part
                    elif frac_and_tz.endswith("Z"):
                        frac = frac_and_tz[:-1]
                        tz_part = "Z"
                    else:
                        frac = frac_and_tz

                    # Pad or truncate fractional seconds to 6 digits
                    frac = (frac + "000000")[:6]
                    normalized = f"{base}.{frac}{tz_part}"
                    return datetime.fromisoformat(normalized).replace(tzinfo=timezone.utc)
                else:
                    raise ValueError(f"No fractional seconds found in: {datetime_str}")
            except Exception as e:
                raise ValueError(f"Invalid datetime format: {datetime_str}") from e

    @staticmethod
    def _hydrate_card(card_data: CardData) -> JPWordCard:
        """
        Convert database card record to JPWordCard object.

        Args:
            card_data: Card data from database

        Returns:
            Hydrated JPWordCard object

        Raises:
            ValueError: If card data is invalid or word JSON cannot be loaded
        """
        try:
            return JPWordCard(
                word=card_data["key"],
                card_id=card_data["id"],
                state=State(int(card_data["state"])),
                step=card_data["step"],
                stability=card_data["stability"],
                difficulty=card_data["difficulty"],
                due=ReviewStateManager._parse_datetime(card_data["due"]),
                last_review=ReviewStateManager._parse_datetime(card_data["last_review"]),
            )
        except (ValueError, KeyError, FileNotFoundError) as e:
            raise ValueError(f"Failed to hydrate card for word '{card_data['key']}' {e}") from e

    def initialize_review(self, auth: dict) -> bool:
        """
        Initialize a new review session with the next due card.

        Args:
            auth: Authentication object with user information

        Returns:
            True if card loaded successfully, False if no cards due

        Raises:
            RuntimeError: If database query fails
        """
        try:
            cards = get_due_card(auth)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch due card: {str(e)}") from e

        if not cards:
            return False

        card_data: CardData = cards[0]
        st.session_state.current_card = card_data.copy()

        try:
            with st.spinner("Generating the question...", show_time=True):
                jpword_card = self._hydrate_card(card_data)

                question = jpword_card.generate_reverse_translation_question(
                    jlpt_level=auth.get("jlpt_level", "N4"),
                    target_languages=auth.get("preferred_languages", ["English"]),
                )

                st.session_state.current_card.update(
                    {
                        "jpword": jpword_card,
                        "qa": question,
                    }
                )
                st.session_state.update(
                    {
                        "review_state": self.STATES["question"],
                        "your_answer": "",
                        "has_ai_review": False,
                    }
                )
        except Exception as e:
            raise RuntimeError(f"Failed to generate question: {str(e)}") from e

        return True

    def transition_to_answer(self) -> None:
        """Transition from question to answer state."""
        st.session_state.review_state = self.STATES["answer"]
        st.rerun()

    def transition_to_submitting(self) -> None:
        """Transition to submitting state."""
        st.session_state.review_state = self.STATES["submitting"]

    def reset(self) -> None:
        """Reset the review state and clean up session variables."""
        try:
            if "review_state" in st.session_state:
                del st.session_state["review_state"]
            if "current_card" in st.session_state:
                del st.session_state["current_card"]
            if "your_answer" in st.session_state:
                del st.session_state["your_answer"]
            if "your_voice_answer" in st.session_state:
                del st.session_state["your_voice_answer"]
            if "ai_review" in st.session_state:
                del st.session_state["ai_review"]
            if "has_ai_review" in st.session_state:
                del st.session_state["has_ai_review"]
            st.rerun()
        except KeyError:
            # State variable already deleted, proceed
            pass

    def get_current_card(self) -> Optional[CurrentCardState]:
        """Get the current card state."""
        return st.session_state.get("current_card", None)

    def get_current_state(self) -> Optional[str]:
        """Get the current review state."""
        return st.session_state.get("review_state", None)

    def set_answer(self, answer: str) -> None:
        """Set the user's answer."""
        st.session_state["your_answer"] = answer

    def get_answer(self) -> str:
        """Get the user's answer."""
        return st.session_state.get("your_answer", "")

    def set_ai_review(self, review: str) -> None:
        """Set the AI review result."""
        st.session_state["ai_review"] = review
        st.session_state["has_ai_review"] = True

    def get_ai_review(self) -> str:
        """Get the AI review result."""
        return st.session_state.get("ai_review", "")

    def has_ai_review(self) -> bool:
        """Check if AI review has been generated."""
        return st.session_state.get("has_ai_review", False)
