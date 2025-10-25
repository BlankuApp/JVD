"""
Japanese word question generation and review service.

This module provides functions for generating reverse translation questions
and reviewing user answers using AI, decoupled from the Card class.
"""

import json
import os
from random import choice
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ReverseTranslationQuestion(BaseModel):
    """Model for reverse translation question and answer."""

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


def load_word_json(word: str) -> dict:
    """
    Load word JSON data from resources.

    Args:
        word: The Japanese word to load

    Returns:
        Dictionary containing word data

    Raises:
        FileNotFoundError: If word JSON file doesn't exist
        json.JSONDecodeError: If JSON file is malformed
    """
    file_path = f"resources/words/{word}.json"
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_random_collocation(word: str) -> str:
    """
    Fetch a random collocation example for the word.

    Args:
        word: The Japanese word

    Returns:
        Random collocation string

    Raises:
        ValueError: If no collocations found for the word
    """
    json_data = load_word_json(word)

    # Support multiple JSON schema versions
    if "collocations" in json_data:
        return choice(json_data["collocations"])
    elif "explanations" in json_data and "collocations" in json_data["explanations"]:
        return choice(json_data["explanations"]["collocations"])
    else:
        raise ValueError(f"No collocations found for word '{word}' with version {json_data.get('version', 'unknown')}")


def generate_reverse_translation_question(
    word: str,
    jlpt_level: str | int = "N4",
    target_languages: Optional[list[str]] = None,
) -> ReverseTranslationQuestion:
    """
    Generate a reverse translation question for a Japanese word.

    Creates a question that asks the user to translate a sentence from
    the target language(s) into Japanese, using the specified word.

    Args:
        word: The Japanese word to create a question for
        jlpt_level: JLPT level for difficulty (default: "N4")
        target_languages: List of target languages for the question (default: ["English"])

    Returns:
        ReverseTranslationQuestion object with question, answer, and hints

    Raises:
        ValueError: If word data cannot be loaded or question generation fails
    """
    if target_languages is None:
        target_languages = ["English"]

    random_collocation = fetch_random_collocation(word)

    prompt = f"""### Role
You are a helpful assistant that creates Japanese language flashcard questions.
You will generate a reverse translation question for the given Japanese word.

### Steps

1. **Create a Sentence as Answer**

   * Generate a short, natural daily-life sentence at {jlpt_level} level using '{word}'. The sentence should look like a part of a conversation or a common statement.
   * You may refer to '{random_collocation}' for context, but do **not** copy it directly. Randomly modify details (e.g., time, place, subject) to create a new sentence.
   * Do not replace the '{word}' with anything else; Make sure it exists in the sentence.
   * Use only {jlpt_level}-appropriate vocabulary besides '{word}'.
   * Consider this as the 'Answer' field in the output.

2. **Translate and Verify as Question**

   * Provide an accurate, literal translation of the generated 'Answer' in {" and ".join(target_languages[:2])}.
   * Consider the translation as the 'Question' field in the output.

3. **Hints**

   * Except '{word}' itself and easy vocabularies, include translations (in {" and ".join(target_languages[:2])}) and readings of the other words in the generated 'Answer'.
   * Separate hints with commas only.
   * Format kanji with readings: e.g., 参加(さんか)する, 賢(かしこ)い.
   * Double check to remove '{word}' from hints.

---

### Example

**Word:** 参加する  |  **Level:** N4  |  **Languages:** English and Persian
**Question:** I will attend the meeting tomorrow / من فردا در جلسه شرکت می‌کنم.
**Answer:** 明日(あした)会議(かいぎ)に参加(さんか)する。
**Hints:** tomorrow: 明日(あした), meeting: 会議(かいぎ)

---

### Constraints
* Makure sure the 'Answer' contains '{word}' or its conjugated forms.
* Exclude '{word}' from hints.
* The 'Answer' is a Japanese sentence; the 'Question' is in {" and ".join(target_languages[:2])}.
* Ensure all kanji have hiragana readings immediately after them.

"""

    # Using gpt-5-mini for cost-effective question generation
    response = client.responses.create(
        model="gpt-5-mini",
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        text={
            "format": {
                "type": "json_schema",
                "name": "math_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                        },
                        "answer": {
                            "type": "string",
                        },
                        "hints": {
                            "type": "string",
                        },
                    },
                    "required": ["question", "answer", "hints"],
                    "additionalProperties": False,
                },
            },
            "verbosity": "low",
        },
        reasoning={"effort": "low", "summary": None},
        tools=[],
        store=False,
        include=[
            "reasoning.encrypted_content",
        ],
    )

    result_dict = json.loads(response.output_text)  # type: ignore
    return ReverseTranslationQuestion(**result_dict)


def review_reverse_translation_question(
    word: str,
    correct_answer: str,
    source_question: str,
    user_answer: str,
    target_languages: Optional[list[str]] = None,
) -> str:
    """
    Review a user's answer to a reverse translation question using AI.

    Args:
        word: The target Japanese word that should be used
        correct_answer: The correct Japanese translation
        source_question: The original question in the target language(s)
        user_answer: The user's Japanese translation attempt
        target_languages: Languages to provide feedback in (default: ["English"])

    Returns:
        Markdown-formatted AI review with score and feedback

    Raises:
        RuntimeError: If AI review generation fails
    """
    if target_languages is None:
        target_languages = ["English"]

    try:
        prompt = f"""
You are a helpful Japanese teacher reviewing a student's answer. Give very short, constructive feedback. The main goal is checking use of '{word}'. Reply in {" and ".join(target_languages[:2])}.
If the student didn't answer, explain the correct answer briefly.

References:
- Correct answer: '{correct_answer}' (ignore readings in parentheses)
- Student answer: '{user_answer}'
- Source sentence (translate fairly): '{source_question}'

Scoring (apply exactly):
1) score = 0
2) If '{word}' appears in any valid form (kanji/kana/reading/conjugation): +10
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
        # Using gpt-5-mini for cost-effective question generation
        response = client.responses.create(
            model="gpt-5-mini",
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            text={
                "format": {
                    "type": "text",
                },
                "verbosity": "low",
            },
            reasoning={"effort": "minimal", "summary": None},
            tools=[],
            store=False,
            include=[
                "reasoning.encrypted_content",
            ],
        )
        return response.output_text  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Failed to generate AI review: {str(e)}") from e


__all__ = [
    "ReverseTranslationQuestion",
    "generate_reverse_translation_question",
    "review_reverse_translation_question",
    "load_word_json",
]
