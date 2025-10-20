"""
fsrs.card
---------

This module defines the Card and State classes.

Classes:
    Card: Represents a flashcard in the FSRS system.
    State: Enum representing the learning state of a Card object.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum
from random import choice

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()

llm_4o_mini_openai = ChatOpenAI(model="gpt-4o", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
llm_5_mini_openai = ChatOpenAI(model="gpt-5-mini", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore


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
        self.json_data = json.loads(open(f"resources/words/{word}.json", "r", encoding="utf-8").read())
        self.question: JPWordCard.ReverseTranslationQuestion | None = None

    def fetch_random_collocation(self) -> str:
        # Fallback for unknown versions - try v0.3.0 format first
        if "collocations" in self.json_data:
            return choice(self.json_data["collocations"])
        elif "explanations" in self.json_data and "collocations" in self.json_data["explanations"]:
            return choice(self.json_data["explanations"]["collocations"])
        else:
            raise ValueError(
                f"No collocations found for word '{self.word}' with version {self.json_data.get('version', 'unknown')}"
            )

    def generate_reverse_translation_question(
        self, jlpt_level: str | int = "N4", target_languages: list[str] = ["English"]
    ) -> JPWordCard.ReverseTranslationQuestion:
        random_collocation = self.fetch_random_collocation()
        structured_llm = llm_4o_mini_openai.with_structured_output(JPWordCard.ReverseTranslationQuestion)
        self.question = structured_llm.invoke(
            [
                HumanMessage(
                    content=f"""
You are a helpful assistant that creates Japanese language flashcard questions.

**Question:** Translation of the Japanese sentence in {" and ".join(target_languages[:2])}.
**Answer:** Japanese sentence containing the target word.
**Hints:** Translations and readings of other words (excluding the target word), separated by commas.

---

### Steps

1. **Create a Sentence as Answer**

   * Generate a short, natural daily-life sentence at {jlpt_level} level using '{self.word}'.
   * You may refer to '{random_collocation}' for context, but do **not** copy it directly.
   * Use only {jlpt_level}-appropriate vocabulary besides '{self.word}'.
   * Consider this as the 'Answer' field in the output.

2. **Translate and Verify as Question**

   * Provide an accurate, literal translation of the generated 'Answer' in {" and ".join(target_languages[:2])}.
   * Consider the translation as the 'Question' field in the output.

3. **Hints**

   * Except '{self.word}', include translations and readings of the other words in the generated 'Answer'.
   * Separate hints with commas only.
   * Format kanji with readings: e.g., 参加(さんか)する, 賢(かしこ)い.
   * Double check to remove '{self.word}' from hints.

---

### Example

**Word:** 参加する  |  **Level:** N4  |  **Languages:** English and Persian
**Question:** I will attend the meeting tomorrow / من فردا در جلسه شرکت می‌کنم.
**Answer:** 明日(あした)会議(かいぎ)に参加(さんか)する。
**Hints:** tomorrow: 明日(あした), meeting: 会議(かいぎ)

---

### Constraints

* Exclude '{self.word}' from hints.
* The question must accurately reflect the Japanese answer.
* Ensure all kanji have hiragana readings immediately after them.

"""
                ),
            ]
        )  # type: ignore
        return self.question  # type: ignore

    def review_reverse_translation_question(self, user_answer: str, target_languages: list[str]) -> str:
        response = llm_4o_mini_openai.invoke(
            [
                HumanMessage(
                    content=f"""
You are a helpful Japanese teacher reviewing a student's answer. Give very short, constructive feedback. The main goal is checking use of '{self.word}'. Reply in {" and ".join(target_languages[:2])}.
If the student didn't answer, explain the correct answer briefly.

References:
- Correct answer: '{getattr(self.question, "answer", "")}' (ignore readings in parentheses)
- Student answer: '{user_answer}'
- Source sentence (translate fairly): '{getattr(self.question, "question", "")}'

Scoring (apply exactly):
1) score = 0
2) If '{self.word}' appears in any valid form (kanji/kana/reading/conjugation): +10
3) If meaning does not match the correct answer: -1 and briefly explain why
4) For each grammar mistake: -1; give a correction + brief reason
   * Ignore minor politeness/verb-form differences (e.g., する/します, です/だ) if meaning is preserved
5) Clamp score to 0-10

Output:
- Review: ultra-brief, one sentence per line, each line begins with an emoji, no headings (≤ ~250 words)
- Then a simple Markdown table listing each +/- with its reason (one row per item)
- End with: `### Overall Score: [score]/10` + an emoji

Before outputting, verify you followed the scoring rules.
"""
                ),
            ]
        )  # type: ignore
        return response.text()


__all__ = ["Card", "State", "JPWordCard"]
