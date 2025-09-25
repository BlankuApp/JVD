import re

import requests

from src import LANGUAGES_ABBR, get_translator_client, get_openai_client
from src.logger_module import get_logger

logger = get_logger("JVD")


def translate_text(text: str, target_language: str, source_language: str | None = "ja") -> str:
    logger.debug(f"🟢Translating text: {text} from {source_language} to {target_language}")
    client = get_translator_client()

    if source_language is None:
        result = client.detect_language(text)
        source_language = result["language"]

    try:
        result = client.translate(text, target_language=target_language, source_language=source_language)
        logger.debug(f"🟢Translation result: {result}")
        return result["translatedText"]
    except Exception as e:
        logger.error(f"🟢Translation failed: {e}")
        return f"Error: {str(e)}"


def translate_to_all_languages(text: str, source_language: str | None = "ja") -> dict:
    logger.debug(f"🟩Translating text to all languages: {text}")
    translations = {}
    for lang_code in LANGUAGES_ABBR.values():
        translated_text = translate_text(text, lang_code, source_language)
        translations[lang_code] = translated_text
    return translations


def query_jisho(word: str) -> dict | None:
    logger.debug(f"🔴Querying Jisho API for word: {word}")
    url = f"https://jisho.org/api/v1/search/words?keyword={word}"
    response = requests.get(url)
    if response.status_code == 200:
        res = response.json()
        data = res.get("data", [])
        if data:
            logger.debug(f"🔴Jisho API response: {data[0]}")
            return data[0]  # Return the first matching entry
        else:
            logger.debug("🔴No data found in Jisho API response")
            return None
    else:
        logger.error(f"🔴Jisho API request failed: {response.status_code}")
        return None


def query_kanji(kanji: str) -> dict | None:
    logger.debug(f"⚪️Querying Kanji API for kanji: {kanji}")
    url = f"https://kanjiapi.dev/v1/kanji/{kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            logger.debug(f"⚪️Kanji API response: {data}")
            return data
        else:
            logger.debug("⚪️No data found in Kanji API response")
            return None
    else:
        logger.error(f"⚪️Kanji API request failed: {response.status_code}")
        return None


def extract_kanji(text) -> list[str]:
    return re.findall(r"[\u4E00-\u9FFF]", text)


class JPWord2:
    def __init__(self, initial_word: str, initial_jlpt_level: int):
        self.word = initial_word
        self.jlpt_level = initial_jlpt_level
        self.jisho_data = query_jisho(self.word)
        self.kanji_data = {}
        if self.jisho_data:
            self.kanji_list = extract_kanji(self.word)
            for kanji in self.kanji_list:
                kanji_info = query_kanji(kanji)
                if kanji_info:
                    self.kanji_data[kanji] = kanji_info
        else:
            self.kanji_list = []
            self.kanji_data = {}

    def get_ai_explanation(self) -> dict:
        client = get_openai_client()
