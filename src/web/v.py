import os
import json

import streamlit as st

from src.db.db_word import (
    add_user_word_card,
    check_user_word_card,
    get_user_word_cards,
    remove_user_word_card,
)
from src import LANGUAGES_ABBR
from src.utils import create_html_with_ruby

auth = st.session_state.get("auth", None)


def show_v3_word_in_streamlit(word_data: dict, auth: dict | None = None) -> None:
    """
    Display a v0.3.0 format word in Streamlit

    Args:
        word_data: Word data in v0.3.0 format (loaded from JSON)
        auth: Optional authentication object with user preferences
    """
    # Title with reading and badges
    word = word_data.get("word", "")
    kanji = word_data.get("kanji", word)
    reading = word_data.get("reading", "")
    jlpt_level = word_data.get("jlpt_level", 5)
    jisho_data = word_data.get("jisho_data", {})
    is_common = jisho_data.get("is_common", False) if jisho_data else False

    if kanji == reading:
        st.markdown(f"# {kanji} :orange-badge[N{jlpt_level}] :green-badge[{'Common' if is_common else 'Uncommon'}]")
    else:
        st.markdown(
            f"# {kanji} ({reading}) :orange-badge[N{jlpt_level}] :green-badge[{'Common' if is_common else 'Uncommon'}]"
        )

    # YouTube video if available
    youtube_link = word_data.get("youtube_link", "")
    if youtube_link:
        st.video(youtube_link)

    # Introduction
    st.markdown(word_data.get("introduction_english", ""))
    st.markdown(word_data.get("introduction_japanese", ""))

    # Meanings
    st.markdown("### Meanings")
    st.markdown(word_data.get("meaning_explanation_english", ""))
    st.markdown(word_data.get("meaning_explanation_japanese", ""))

    # Meaning translations
    for meaning_dict in word_data.get("meanings_translations", []):
        with st.container(border=True, horizontal=True):
            for lang_code, translation in meaning_dict.items():
                if auth:
                    user_langs = [LANGUAGES_ABBR.get(lang, lang) for lang in auth.get("preferred_languages", [])]
                    if lang_code not in user_langs:
                        continue
                if lang_code == "EN":
                    st.markdown(
                        f":blue-badge[{lang_code}] {', '.join(translation) if isinstance(translation, list) else translation}"
                    )
                else:
                    st.markdown(f":blue-badge[{lang_code}] {translation}")

    # Synonyms and Antonyms
    synonym_explanation = word_data.get("synonym_explanation", "")
    antonym_explanation = word_data.get("antonym_explanation", "")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Synonyms")
        with st.container(border=True):
            synonyms = word_data.get("synonyms", [])
            if synonyms:
                for s in synonyms:
                    st.markdown(s)
                if synonym_explanation:
                    with st.expander("Explanation"):
                        st.markdown(synonym_explanation)
            else:
                st.markdown("_No synonyms available_")

    with col2:
        st.markdown("### Antonyms")
        with st.container(border=True):
            antonyms = word_data.get("antonyms", [])
            if antonyms:
                for a in antonyms:
                    st.markdown(a)
                if antonym_explanation:
                    with st.expander("Explanation"):
                        st.markdown(antonym_explanation)
            else:
                st.markdown("_No antonyms available_")

    # Kanji breakdown
    st.markdown("### Kanji")
    kanji_list = word_data.get("kanji_list", [])
    kanji_data = word_data.get("kanji_data", {})
    kanji_details = word_data.get("kanji_details", [])

    for i, k in enumerate(kanji_list):
        if k in kanji_data:
            cont = st.container(border=True)
            col1, col2 = cont.columns([2, 4])

            with col1:
                unicode_hex = kanji_data[k].get("unicode", "")
                if unicode_hex:
                    st.image(
                        f"https://raw.githubusercontent.com/KanjiVG/kanjivg/refs/heads/master/kanji/0{unicode_hex.lower()}.svg",
                        width="content",
                    )

            with col2:
                meanings = kanji_data[k].get("meanings", [])
                on_readings = kanji_data[k].get("on_readings", [])
                kun_readings = kanji_data[k].get("kun_readings", [])

                st.markdown(f":gray-badge[Meaning] {', '.join(meanings)}")
                st.markdown(f":gray-badge[On-yomi] {', '.join(on_readings)}")
                st.markdown(f":gray-badge[Kun-yomi] {', '.join(kun_readings)}")
                st.markdown("---")

                # Show common words from kanji_details if available
                if i < len(kanji_details) and "common_words" in kanji_details[i]:
                    for common_word in kanji_details[i]["common_words"]:
                        st.markdown(common_word)

    # Kanji explanation
    kanji_explanation = word_data.get("kanji_explanation", "")
    if kanji_explanation:
        with st.expander("Kanji Explanation"):
            st.markdown(kanji_explanation)

    # Example sentences
    st.markdown("### Examples")
    example_sentences = word_data.get("example_sentences", [])
    for ex in example_sentences:
        kanji_text = ex.get("kanji", "")
        furigana = ex.get("furigana", "")
        translations = ex.get("translations", {})

        with st.expander(kanji_text):
            if furigana:
                ruby = create_html_with_ruby(furigana)
                st.markdown(ruby, unsafe_allow_html=True)

            for lang_code, translation in translations.items():
                if auth:
                    user_langs = [LANGUAGES_ABBR.get(lang, lang) for lang in auth.get("preferred_languages", [])]
                    if lang_code not in user_langs:
                        continue
                st.markdown(f":gray-badge[{lang_code}] {translation}")

    # Collocations
    st.markdown("### Collocations")
    collocations = word_data.get("collocations", [])
    if collocations:
        for collocation in collocations[:10]:  # Show first 10
            if isinstance(collocation, dict):
                collocation_kanji = collocation.get("kanji", "")
                collocation_furigana = collocation.get("furigana", "")
                collocation_translations = collocation.get("translations", {})

                with st.expander(collocation_kanji):
                    if collocation_furigana and collocation_furigana != collocation_kanji:
                        ruby = create_html_with_ruby(collocation_furigana)
                        st.markdown(ruby, unsafe_allow_html=True)

                    if collocation_translations:
                        for lang_code, translation in collocation_translations.items():
                            if auth:
                                user_langs = [
                                    LANGUAGES_ABBR.get(lang, lang) for lang in auth.get("preferred_languages", [])
                                ]
                                if lang_code not in user_langs:
                                    continue
                            st.markdown(f":gray-badge[{lang_code}] {translation}")
                    else:
                        st.markdown("_No translations available_")
            elif isinstance(collocation, str):
                st.markdown(f"- {collocation}")


def fetch_and_show_word():
    """Load and display the word from query params"""
    file_path = "resources/words/" + st.query_params["w"] + ".json"
    with open(file_path, "r", encoding="utf-8") as file:
        word_data = json.load(file)

    version = word_data.get("version", "")

    # Check if it's v0.3.0 format
    if version.startswith("0.3"):
        show_v3_word_in_streamlit(word_data, auth)
    else:
        # For older versions, show a warning
        st.warning(
            f"⚠️ This word is in an older format (version: {version}). Please migrate to v0.3.0 for full display."
        )


@st.cache_data(ttl=3600)
def get_words() -> list[dict]:
    words = []
    json_files = [f for f in os.listdir("resources/words") if f.endswith(".json")]
    for json_file in json_files:
        with open(os.path.join("resources/words", json_file), "r", encoding="utf-8") as file:
            raw_data = file.read()
            json_data = json.loads(raw_data)
            words.append(dict(word=json_data["word"], level=json_data["jlpt_level"]))
    return words


if "w" in st.query_params:
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if st.button(":arrow_left: Back to Vocabularies"):
            st.query_params.pop("w")
            st.rerun()
        card_added = check_user_word_card(auth, st.query_params["w"]) if auth else False
        if card_added:
            if st.button(":star: remove from My Words"):
                if auth:
                    result = remove_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to manage your words.", icon="❌")
        else:
            if st.button(":star: Add to My Words", type="primary"):
                if auth:
                    result = add_user_word_card(auth, st.query_params["w"])
                    st.toast(result[1], icon="✅" if result[0] else "❌")
                    st.rerun()
                else:
                    st.toast("You need to be logged in to add words to your list.", icon="❌")
    fetch_and_show_word()
else:
    user_word_cards = get_user_word_cards(auth) if auth else []
    marked_words = [w.get("key") for w in user_word_cards] if user_word_cards else []
    words = get_words()
    st.markdown("# JLPT Vocabularies")

    for level in [4, 3, 2]:
        with st.expander(f"N{level} Vocabularies"):
            with st.container(horizontal=True):
                for w in words:
                    if w.get("level") == level:
                        word = str(w.get("word", ""))
                        if st.button(word, type="primary" if word in marked_words else "secondary"):
                            st.query_params.update({"w": word})
                            st.rerun()
