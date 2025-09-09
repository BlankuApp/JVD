"""
fsrs.card
---------

This module defines the Card and State classes.

Classes:
    Card: Represents a flashcard in the FSRS system.
    State: Enum representing the learning state of a Card object.
"""

from __future__ import annotations
from enum import IntEnum
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from src.word.JPWord import JPWord
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from random import choice

load_dotenv()

llm_4o_mini_openai = ChatOpenAI(model="gpt-4o-mini", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
llm_5_nano_openai = ChatOpenAI(model="gpt-4o", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore


class State(IntEnum):
    """
    Enum representing the learning state of a Card object.
    """

    Learning = 1
    Review = 2
    Relearning = 3


@dataclass(init=False)
class Card:
    """
    Represents a flashcard in the FSRS system.

    Attributes:
        card_id: The id of the card. Defaults to the epoch milliseconds of when the card was created.
        state: The card's current learning state.
        step: The card's current learning or relearning step or None if the card is in the Review state.
        stability: Core mathematical parameter used for future scheduling.
        difficulty: Core mathematical parameter used for future scheduling.
        due: The date and time when the card is due next.
        last_review: The date and time of the card's last review.
    """

    card_id: int
    state: State
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime | None

    def __init__(
        self,
        card_id: int | None = None,
        state: State = State.Learning,
        step: int | None = None,
        stability: float | None = None,
        difficulty: float | None = None,
        due: datetime | None = None,
        last_review: datetime | None = None,
    ) -> None:
        if card_id is None:
            # epoch milliseconds of when the card was created
            card_id = int(datetime.now(timezone.utc).timestamp() * 1000)
            # wait 1ms to prevent potential card_id collision on next Card creation
            time.sleep(0.001)
        self.card_id = card_id

        self.state = state

        if self.state == State.Learning and step is None:
            step = 0
        self.step = step

        self.stability = stability
        self.difficulty = difficulty

        if due is None:
            due = datetime.now(timezone.utc)
        self.due = due

        self.last_review = last_review

    def to_dict(self) -> dict[str, int | float | str | None]:
        """
        Returns a JSON-serializable dictionary representation of the Card object.

        This method is specifically useful for storing Card objects in a database.

        Returns:
            A dictionary representation of the Card object.
        """

        return_dict = {
            "card_id": self.card_id,
            "state": self.state.value,
            "step": self.step,
            "stability": self.stability,
            "difficulty": self.difficulty,
            "due": self.due.isoformat(),
            "last_review": self.last_review.isoformat() if self.last_review else None,
        }

        return return_dict

    @staticmethod
    def from_dict(source_dict: dict[str, int | float | str | None]) -> Card:
        """
        Creates a Card object from an existing dictionary.

        Args:
            source_dict: A dictionary representing an existing Card object.

        Returns:
            A Card object created from the provided dictionary.
        """

        card_id = int(source_dict["card_id"])
        state = State(int(source_dict["state"]))
        step = source_dict["step"]
        stability = float(source_dict["stability"]) if source_dict["stability"] else None
        difficulty = float(source_dict["difficulty"]) if source_dict["difficulty"] else None
        due = datetime.fromisoformat(source_dict["due"])
        last_review = datetime.fromisoformat(source_dict["last_review"]) if source_dict["last_review"] else None

        return Card(
            card_id=card_id,
            state=state,
            step=step,
            stability=stability,
            difficulty=difficulty,
            due=due,
            last_review=last_review,
        )


@dataclass(init=False)
class JPWordCard(Card):
    """
    Represents a flashcard for a Japanese word in the FSRS system.

    Attributes:
        word: The Japanese word associated with the card.
    """

    class ReverseTranslationQuestion(BaseModel):
        question: str = Field(
            default="",
            description="The sentence that asks for the translation to Japanese. E.g., 'I will attend the meeting.'",
        )
        answer: str = Field(
            default="", description="The correct translation of the question into Japanese. E.g., '会議に参加する。'"
        )
        hints: str = Field(
            default="",
            description="Except the main word, provide translations for other words in the sentence as hints. E.g., 'meeting: 会議'",
        )

    word: str

    def __init__(
        self,
        word: str,
        card_id: int | None = None,
        state: State = State.Learning,
        step: int | None = None,
        stability: float | None = None,
        difficulty: float | None = None,
        due: datetime | None = None,
        last_review: datetime | None = None,
    ) -> None:
        super().__init__(
            card_id=card_id,
            state=state,
            step=step,
            stability=stability,
            difficulty=difficulty,
            due=due,
            last_review=last_review,
        )
        self.word = word
        self._jp_word: JPWord = JPWord.model_validate_json(
            open(f"resources/words/{word}.json", "r", encoding="utf-8").read()
        )

    def fetch_random_collocation(self) -> str:
        return choice(self._jp_word.explanations.collocations) if self._jp_word.explanations.collocations else ""

    def generate_reverse_translation_question(
        self, jlpt_level: str | int = "N4", target_languages: list[str] = ["English"]
    ) -> JPWordCard.ReverseTranslationQuestion:
        random_collocation = self.fetch_random_collocation()
        structured_llm = llm_5_nano_openai.with_structured_output(JPWordCard.ReverseTranslationQuestion)
        question = structured_llm.invoke(
            [
                SystemMessage(
                    content=f"You are a helpful assistant that generates language learning flashcard questions. The answer is the Japanese sentence containing the target word. The question is the translation of the sentence in {' and '.join(target_languages)}. Hints are translations and reading of other words in the sentence except the target word."
                ),
                HumanMessage(
                    content=f"""# Tasks
1. Generate a simple, natural and short, {jlpt_level} level sentence with '{self.word}' as the answer. You can use the collocation '{random_collocation}' as a template.
2. provide the accurate and natural translation of answer in {" and ".join(target_languages)} as the question. The kanjis in the question sentence should be followed by its hiragana reading in parentheses.
3. Hints are translations and reading of other words in the sentence except the target word. Make sure the '{self.word}' is not included in the hints. 
# Example:
Example for word '参加する' with target language 'English and Persian' and level 'N4':
Question: I will attend the meeting / من در جلسه شرکت میکنم.
Answer: 会議(かいぎ)に参加(さんか)する。
Hints: meeting: 会議(かいぎ)
# Constraints:
- Remove '{self.word}' from the hints.
- The question must be a natural and accurate translation of the answer.
- In the answer, the kanjis must be followed by their hiragana reading in parentheses.
"""
                ),
            ]
        )
        return question


__all__ = ["Card", "State", "JPWordCard"]
