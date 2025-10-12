import json
import pprint
from typing import Annotated, Any, List

from pydantic import BaseModel, ConfigDict, Field

from src import LANGUAGES_ABBR, get_translator_client
from src.logger_module import get_logger
from src.word.JPWord import extract_kanji, query_jisho, query_kanji

logger = get_logger("JVD")


def translate_text(text: str, target_language: str, source_language: str | None = "ja") -> str:
    """Translate text from source language to target language using Google Translate"""
    logger.debug(f"🟢 Translating text: {text} from {source_language} to {target_language}")
    client = get_translator_client()

    if source_language is None:
        result = client.detect_language(text)
        source_language = result["language"]

    try:
        result = client.translate(
            text, target_language=target_language, source_language=source_language, format_="text"
        )
        logger.debug(f"🟢 Translation result: {result}")
        return result["translatedText"]
    except Exception as e:
        logger.error(f"🟢 Translation failed: {e}")
        return f"Error: {str(e)}"


def translate_to_all_languages(text: str, source_language: str | None = "ja") -> dict:
    """Translate text to all supported languages"""
    logger.debug(f"🟩 Translating text to all languages: {text}")
    translations = {}
    for lang_code in LANGUAGES_ABBR.values():
        if lang_code.lower() == source_language.lower():
            continue
        translated_text = translate_text(text, lang_code, source_language)
        translations[lang_code] = translated_text
    order_list = ["EN", "ID", "ES", "VI", "FR", "NE", "BN", "ZH", "KO", "TL", "MY", "HI", "AR", "FA"]
    sorted_x = {key: translations[key] for key in order_list if key in translations}
    return sorted_x


class KanjiDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kanji: str = Field(examples=["学", "校"], max_length=1, additionalProperties=False)  # type: ignore
    onyomi: list[str] = Field(
        min_items=0, max_items=2, examples=[["がく"], ["こう", "きょう"]], additionalProperties=False
    )  # type: ignore
    kunyomi: list[str] = Field(
        min_items=0, max_items=2, examples=[["まな.ぶ"], ["つか.う", "つか.える"]], additionalProperties=False
    )  # type: ignore
    meanings_english: list[str] = Field(
        min_items=1, max_items=3, examples=[["study", "learning"], ["school", "exam"]], additionalProperties=False
    )  # type: ignore
    common_words: list[str] = Field(
        min_items=1,
        max_items=2,
        examples=[
            ["土曜日 (どようび): Saturday", "土地 (とち): land, plot"],
            ["出産 (しゅっさん): childbirth", "産業 (さんぎょう): industry"],
        ],
        additionalProperties=False,
    )  # type: ignore


NuanceList = Annotated[
    List[Annotated[str, Field(max_length=20, description="single english word")]], Field(min_items=1, max_items=5)  # type: ignore
]


class JapaneseText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kanji: str = Field(examples=["本を読む"], max_length=100, additionalProperties=False)  # type: ignore
    furigana: str = Field(examples=["本(ほん)を読(よ)む"], max_length=100, additionalProperties=False)  # type: ignore
    translations: dict[str, str] = Field(default_factory=dict)  # COMMENT OUT THIS LINE BEFORE RUNNING BATCH


class JPWordInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kanji: str = Field(examples=["学校", "猫", "走る"], max_length=4, additionalProperties=False)  # type: ignore
    reading: str = Field(examples=["がっこう", "ねこ", "はしる"], max_length=8, additionalProperties=False)  # type: ignore
    introduction_japanese: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    introduction_english: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    meanings: List[NuanceList] = Field(
        min_items=1,
        max_items=3,
        examples=[[["degree", "level", "amount"], ["balance", "moderation"]]],
        additionalProperties=False,
    )  # type: ignore
    meaning_explanation_japanese: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    meaning_explanation_english: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    youtube_description: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    kanji_details: list[KanjiDetail] = Field(min_items=1, max_items=4)  # type: ignore
    kanji_explanation: str = Field(max_length=500, additionalProperties=False)  # type: ignore
    synonyms: list[Annotated[str, Field(max_length=50)]] = Field(
        min_items=0, max_items=2, examples=[["土産 : みやげ : souvenir", "贈り物 : おくりもの : gift, present"]]
    )  # type: ignore
    synonym_explanation: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    antonyms: list[Annotated[str, Field(max_length=50)]] = Field(
        min_items=0, max_items=2, examples=[["暑い : あつい : hot", "高い : たかい : tall, high"]]
    )  # type: ignore
    antonym_explanation: str = Field(max_length=250, additionalProperties=False)  # type: ignore
    collocations: list[JapaneseText] = Field(min_items=5, max_items=8)  # type: ignore
    example_sentences: list[JapaneseText] = Field(min_items=4, max_items=5)  # type: ignore
    meanings_translations: list[dict[str, Any]] = Field(
        default_factory=list
    )  # COMMENT OUT THIS LINE BEFORE RUNNING BATCH

    def add_translations_to_examples(self):
        """
        Add translations to all example sentences by translating the kanji text
        to all supported languages. Modifies the example_sentences in place.
        """
        logger.info(f"Adding translations to example sentences for word: {self.kanji}")
        for example in self.example_sentences:
            # Get the kanji text to translate
            text_to_translate = example.kanji
            logger.debug(f"Translating example: {text_to_translate}")

            # Translate to all languages
            translations = translate_to_all_languages(text_to_translate, source_language="ja")

            # Set translations field
            example.translations = translations

        logger.info(f"Successfully added translations to {len(self.example_sentences)} examples")
        return self

    def add_translations_to_collocations(self):
        """
        Add translations to all collocations by translating the kanji text
        to all supported languages. Modifies the collocations in place.
        """
        logger.info(f"Adding translations to collocations for word: {self.kanji}")
        for collocation in self.collocations:
            # Get the kanji text to translate
            text_to_translate = collocation.kanji
            logger.debug(f"Translating collocation: {text_to_translate}")

            # Translate to all languages
            translations = translate_to_all_languages(text_to_translate, source_language="ja")

            # Set translations field
            collocation.translations = translations

        logger.info(f"Successfully added translations to {len(self.collocations)} collocations")
        return self

    def add_translations_to_meanings(self):
        """
        Add translations to all meanings by translating each nuance word
        to all supported languages. Modifies the meanings in place.
        """
        logger.info(f"Adding translations to meanings for word: {self.kanji}")
        for nuance_list in self.meanings:
            translations = translate_to_all_languages(nuance_list[0], source_language="en")
            translations["EN"] = nuance_list
            self.meanings_translations.append(translations)

    def add_all_translations(self):
        """
        Add translations to both example sentences and collocations.
        Convenience method to translate all text content.
        """
        logger.info(f"Adding translations to all text content for word: {self.kanji}")
        self.add_translations_to_examples()
        self.add_translations_to_collocations()
        self.add_translations_to_meanings()
        logger.info("Successfully added all translations")
        return self


prompt_template = """You are a friendly teacher who explains Japanese vocabulary to beginners. Use a clear, concise, spoken style (as if to a friend). Keep every section brief but complete.

Target word: {{word}}

Output the sections below using **exactly** these headings and this order—no extra commentary.

## introduction_japanese
In Japanese only. Without giving the meaning or reading, name typical situations/contexts where this word is used. Start with the word itself. 1–2 short spoken sentences suitable for elementary learners.

## introduction_english
English translation of **introduction_japanese**. Write the word in kana. Start with: “The [adjective/noun/verb …] [word] …”

## youtube_description
A short English YouTube description for a video explaining the word’s meaning and use.

## meanings
List **all** meanings grouped by nuance. Each nuance is a list of single-word English glosses. Return a nested list, e.g.:
[[degree,level,amount],[balance,moderation]]

## meaning_explanation_japanese
A short, complete spoken explanation (Japanese) of the literal meanings based on the previous meanings section. Do **not** use the target word itself—use synonyms or antonyms.

## meaning_explanation_english
A short spoken explanation (English) of the literal meanings  based on the previous meanings section. Include the word in kana.

## kanji_details
For **each kanji** in the word: give 1–2 common words (excluding the target word). For each, provide: kanji word, reading, and meaning.

## kanji_explanation_english
For **each kanji** (in order), write one paragraph of 3–4 short sentences in a teacher’s spoken voice. Start with “The [first/second/…] kanji means …”. Mention 1–2 example vocab items (not the target word) **written in hiragana only**. No bullet points, parentheses, line breaks, titles, or kanji inside the example vocab.

## synonyms
List 1 (max 2) common synonyms **excluding the target word**. Format exactly:
kanji : reading : meaning

## synonyms_explanation
A very short English explanation of the synonyms’ nuances and how they overlap with the target word. Start with: “The most common synonym[s] of the word [are/is] …”. Write any Japanese vocab **in hiragana only** (no kanji).

## antonyms
List 1 (max 2) common antonyms **excluding the target word**. Format exactly:
kanji : reading : meaning

## antonyms_explanation
A very short English explanation of the antonyms’ nuances and how they differ from the target word. Start with: “The most common antonym[s] of the word [are/is] …”. Write any Japanese vocab **in hiragana only** (no kanji).

## collocations
Collocation refers to a group of two or more words that usually go together.
List simple, common collocations based on each of the following patterns with the word ({{word}}). 
1) Noun Phrase (Det/Num + Adj + N; N + Adj; N + N; Poss + N; N + case/PP)
2) Verb Phrase (S + V + O; V + Adv; V + Obj + PP; Aux + V; serial V if normal)
3) Adjective Phrase (Adv + Adj; Adj + PP; basic comparatives/superlatives)
4) Adverbial Phrase (Adv + Adv; Adv + PP; common time/place adverbials)
For example {kanji:鋭い痛み, furigana:鋭(するど)い痛(いた)み}, {kanji:営業を開始する, furigana:営業(えいぎょう)を開始(かいし)する}, {kanji:週末の営業, furigana:週末(しゅうまつ)の営業(えいぎょう)}.

## Examples
Provide 5–7 short, simple sentences using the target word in different contexts aligned with the collocations. 

For each collocation and example, give:
- Kanji sentence
- Furigana sentence, placing the reading in parentheses **immediately after each kanji** (if no kanji, write the sentence once).
Keep everything beginner-friendly.
"""

ws = [
    "移す",
    "営業",
    "解決",
    "火災",
]


def get_schema():
    # Make sure to comment out the translations in JPWordInfo before running this function
    # also comment out meanings_translations in JPWordInfo and translations in JapaneseText

    openai_schema = {
        "name": "jp_word_info",
        "type": "json_schema",
        "strict": True,
        "schema": {**JPWordInfo.model_json_schema(), "additionalProperties": False},
    }

    openai_schema_string = str(openai_schema).replace("'", '"').replace("True", "true").replace("False", "false")
    return openai_schema


def generate_word_requests(words: list[str]):
    # fmt: off
    # fmt: on
    openai_schema = get_schema()
    with open("batch_words.jsonl", "w", encoding="utf-8") as f:
        for word in words:
            print(f"Processing word: {word}")
            request = {
                "custom_id": word,
                "method": "POST",
                "url": "/v1/responses",
                "body": {
                    "model": "gpt-5",
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": prompt_template.replace("{{word}}", word),
                                }
                            ],
                        }
                    ],
                    "text": {"format": openai_schema, "verbosity": "high"},
                    "reasoning": {"effort": "medium", "summary": None},
                    "tools": [],
                    "store": False,
                    "include": ["reasoning.encrypted_content", "web_search_call.action.sources"],
                },
            }
            f.write(
                request.__str__()
                .replace("'", '"')
                .replace("True", "true")
                .replace("False", "false")
                .replace("None", "null")
                + "\n"
            )


def read_batch_results(filepath: str, jlpt_level: int):
    outputs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            result = json.loads(line)
            word = result["custom_id"]
            with open(f"{word}_batch.json", "w", encoding="utf-8") as wf:
                data = eval(result["response"]["body"]["output"][1]["content"][0]["text"])
                jp_w = JPWordInfo.model_validate(data)
                jp_w.add_all_translations()
                outputs.append((word, jp_w))
                d = {
                    "version": "0.3.0",
                    "word": word,
                    "jlpt_level": jlpt_level,
                    "youtube_link": "",
                    "in_db": False,
                    **jp_w.model_dump(),
                    "jisho_data": query_jisho(word),
                    "kanji_list": extract_kanji(word),
                    "kanji_data": {k: query_kanji(k) for k in extract_kanji(word)},
                }
                json.dump(d, wf, ensure_ascii=False, indent=2)
    return outputs


if __name__ == "__main__":
    # get_schema()
    # generate_word_requests(ws)
    w = read_batch_results(r"C:\Users\eskan\Downloads\batch_68ebaf6956e0819090f86166d6593f31_output.jsonl", 3)
    # print(w)
