"""
py-fsrs
-------

Py-FSRS is the official Python implementation of the FSRS scheduler algorithm, which can be used to develop spaced repetition systems.
"""

from src.pyfsrs.fsrs.scheduler import Scheduler
from src.pyfsrs.fsrs.card import Card, State, JPWordCard
from src.pyfsrs.fsrs.review_log import ReviewLog, Rating


# lazy load the Optimizer module due to heavy dependencies
def __getattr__(name: str) -> type:
    if name == "Optimizer":
        global Optimizer
        from fsrs.optimizer import Optimizer

        return Optimizer
    raise AttributeError


__all__ = ["Scheduler", "Card", "Rating", "ReviewLog", "State", "JPWordCard", "Optimizer"]
