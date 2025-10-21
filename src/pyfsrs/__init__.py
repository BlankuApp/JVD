"""
py-fsrs
-------

Py-FSRS is the official Python implementation of the FSRS scheduler algorithm, which can be used to develop spaced repetition systems.
"""

from src.pyfsrs.scheduler import Scheduler
from src.pyfsrs.card import Card, State
from src.pyfsrs.review_log import ReviewLog, Rating
from src.pyfsrs.question_service import (
    ReverseTranslationQuestion,
    generate_reverse_translation_question,
    review_reverse_translation_question,
    load_word_json,
)


# lazy load the Optimizer module due to heavy dependencies
def __getattr__(name: str) -> type:
    if name == "Optimizer":
        global Optimizer
        from optimizer import Optimizer

        return Optimizer
    raise AttributeError


__all__ = [
    "Scheduler",
    "Card",
    "Rating",
    "ReviewLog",
    "State",
    "Optimizer",
    "ReverseTranslationQuestion",
    "generate_reverse_translation_question",
    "review_reverse_translation_question",
    "load_word_json",
]
