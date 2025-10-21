"""
Utility functions for Japanese word processing.

This module contains utility functions for translating text, querying external APIs
(Jisho and Kanji API), and extracting kanji from Japanese text.
"""

import re

import requests

from src import LANGUAGES_ABBR, get_translator_client
from src.logger_module import get_logger

logger = get_logger("JVD")


def translate_text(text: str, target_language: str, source_language: str | None = "ja") -> str:
    """Translate text from source language to target language using Google Translate"""
    logger.debug(f"🟢 Translating text: {text} from {source_language} to {target_language}")
    client = get_translator_client()

    if source_language is None:
        result = client.detect_language(text)
        source_language = result["language"]

    try:
        # normalize language codes to lowercase for the translator API
        tgt = target_language.lower() if isinstance(target_language, str) else target_language
        src = source_language.lower() if isinstance(source_language, str) else source_language
        result = client.translate(text, target_language=tgt, source_language=src, format_="text")
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
        # skip translating to the same language as source (guard if source_language is None)
        if source_language and lang_code.lower() == source_language.lower():
            continue
        translated_text = translate_text(text, lang_code, source_language)
        translations[lang_code] = translated_text
    order_list = ["EN", "ID", "ES", "VI", "FR", "NE", "BN", "ZH", "KO", "TL", "MY", "HI", "AR", "FA"]
    sorted_x = {key: translations[key] for key in order_list if key in translations}
    return sorted_x


def query_jisho(word: str) -> dict | None:
    """Query Jisho API for Japanese word definitions"""
    logger.debug(f"🔴 Querying Jisho API for word: {word}")
    url = f"https://jisho.org/api/v1/search/words?keyword={word}"
    response = requests.get(url)
    if response.status_code == 200:
        res = response.json()
        data = res.get("data", [])
        if data:
            logger.debug(f"🔴 Jisho API response: {data[0]}")
            return data[0]  # Return the first matching entry
        else:
            logger.debug("🔴 No data found in Jisho API response")
            return None
    else:
        logger.error(f"🔴 Jisho API request failed: {response.status_code}")
        return None


def query_kanji(kanji: str) -> dict | None:
    """Query Kanji API for kanji information"""
    logger.debug(f"⚪️ Querying Kanji API for kanji: {kanji}")
    url = f"https://kanjiapi.dev/v1/kanji/{kanji}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            logger.debug(f"⚪️ Kanji API response: {data}")
            return data
        else:
            logger.debug("⚪️ No data found in Kanji API response")
            return None
    else:
        logger.error(f"⚪️ Kanji API request failed: {response.status_code}")
        return None


def extract_kanji(text) -> list[str]:
    """Extract kanji characters from Japanese text using Unicode range"""
    return re.findall(r"[\u4E00-\u9FFF]", text)
