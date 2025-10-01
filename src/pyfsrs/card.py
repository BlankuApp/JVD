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
        if self.json_data["version"] == "0.1.1":
            return choice(self.json_data["explanations"]["collocations"])
        elif self.json_data["version"] == "0.2.0":
            return choice(self.json_data["collocations"])

    def generate_reverse_translation_question(
        self, jlpt_level: str | int = "N4", target_languages: list[str] = ["English"]
    ) -> JPWordCard.ReverseTranslationQuestion:
        random_collocation = self.fetch_random_collocation()
        structured_llm = llm_4o_mini_openai.with_structured_output(JPWordCard.ReverseTranslationQuestion)
        self.question = structured_llm.invoke(
            [
                SystemMessage(
                    content=f"You are a helpful assistant that generates language learning flashcard questions. The answer is the Japanese sentence containing the target word. The question is the translation of the sentence in {' and '.join(target_languages[:2])}. Hints are translations and reading of other words in the sentence except the target word. Always double-check translation quality by back-translating the Japanese answer into the target language(s) and ensuring the meaning matches the question. If a discrepancy is found, revise the translation until it is accurate and natural."
                ),
                HumanMessage(
                    content=f"""# Tasks
1. Generate a random, natural (daily life) and short, {jlpt_level} level sentence with '{self.word}' as the answer. You can use the collocation '{random_collocation}' as an sample context, but don't dirrectly use the collocation in the sentence. Except the target word '{self.word}', please make sure to use random words that are within the {jlpt_level} level.
2. Provide an accurate and literal translation of the answer in {" and ".join(target_languages[:2])} as the question. Always perform a back-translation check: translate the generated Japanese answer back into the target language(s) and compare it to the question. If the meaning or nuance differs, correct the translation until it matches the Japanese sentence. If there is ambiguity in translating a phrase add some notes in parentheses.
3. Hints are translations and reading of other words in the sentence except the target word. Make sure the '{self.word}' is not included in the hints. 
4. Hints are separated by commas. nothing else.
5. Make sure in the answer, the kanjis are followed by their hiragana reading in parentheses. for example, 参加(さんか)する and 賢(かしこ)い not 賢い(かしこい)
# Example:
Example for word '参加する' with target language 'English and Persian' and level 'N4':
Question: I will attend the meeting tomorrow / من فردا در جلسه شرکت میکنم.
Answer: 明日(あした)会議(かいぎ)に参加(さんか)する。
Hints: tomorrow: 明日(あした), meeting: 会議(かいぎ)
# Constraints:
- Remove '{self.word}' from the hints.
- The question must be a natural and accurate translation of the answer.
- In the answer, the kanjis must be followed by their hiragana reading in parentheses.
"""
                ),
            ]
        )  # type: ignore
        return self.question  # type: ignore

    def review_reverse_translation_question(self, user_answer: str, target_languages: list[str]) -> str:
        response = llm_4o_mini_openai.invoke(
            [
                SystemMessage(
                    content=f"""You are a helpful Japanese teacher that is reviewing your student's answer and providing very short and constructive feedback. The goal of this question was to make sure student could remember and use '{self.word}'. Answer in {" and ".join(target_languages[:2])}."""
                ),
                SystemMessage(
                    content=f"""Scoring rules (apply exactly):
1) Start from 0 points.
2) If the target word '{self.word}' appears in the student's answer in any acceptable form (kanji, kana/reading, or any conjugated form), GRANT +5 points.
3) If the student's answer does NOT convey the same meaning as the correct answer, DEDUCT 1 point and include a short explanation why (one sentence).
4) For each grammatical mistake in the student's answer, DEDUCT 1 point and provide a short correction with an explanation (one sentence per mistake).
5) After applying grants and deductions, CLAMP the final score to the range 0 to 5.
6) Keep the review text very short and focused; the breakdown table and the Overall Score line are required.
Double-check these rules before producing the final output.
"""
                ),
                HumanMessage(
                    content=f"""The **correct answer** is '{getattr(self.question, "answer", "")}' (ignore the hiragana readings in parentheses) and the **students's answer** is '{user_answer}'.
Consider the fact that the user tried to translate the following sentence to Japanese: '{getattr(self.question, "question", "")}'. So try to have fairness in your review.
--- Scoring rules (apply exactly):
* check if the target word '{self.word}' or its hiragana reading or its conjugated form is used in the **student's answer** ('{user_answer}'). If it is used in any acceptable form, grant +5 points (see rules above).
* The goal is to make sure the **student's answer** conveys the general meaning of the **correct answer**. If the meaning is not conveyed, deduct 1 point and explain briefly why.
* Correct any grammar mistakes in the **student's answer** ('{user_answer}') with a short correction and explanation (1 point deduction per mistake). Leave this blank if there are no mistakes.
* Ignore minor verb-form/politeness differences (e.g., する vs します, です vs だ) or small structural variations as long as meaning is preserved.
* After counting grants and deductions, clamp the final score to the 0-5 range and present it as the Overall Score.
* Keep the review text very short (max ~250 words for the review lines). The breakdown table may be slightly longer but keep it concise.
Output format:
[Your review here with proper emojis (no headings at all, each sentence in a new line starting with an emoji)]
Make a simple table showing each + or - with the reason (one line per row).
### Overall Score: [score]/5 [with proper emojis]

Double-check the scoring rules before returning the final message.
"""
                ),
            ]
        )  # type: ignore
        return response.text()


__all__ = ["Card", "State", "JPWordCard"]
