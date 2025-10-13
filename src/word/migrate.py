import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.logger_module import get_logger
from src import LANGUAGES_ABBR

logger = get_logger("JVD")


def migrate_word_v1_to_v2(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert JPWord v0.1.1 format to v0.2.0 format

    Args:
        v1_data: Word data in v0.1.1 format

    Returns:
        Word data in v0.2.0 format
    """
    logger.info(f"🔄 Migrating word '{v1_data.get('word', 'unknown')}' from v0.1.1 to v0.2.0")

    # Extract basic info
    word = v1_data.get("word", "")
    reading = v1_data.get("reading", "")
    jlpt_list = v1_data.get("jlpt", [])

    # Convert JLPT to numeric level
    jlpt_level = _extract_jlpt_level(jlpt_list)

    # Build v0.2.0 structure
    v2_data = {
        "version": "0.2.0",
        "word": word,
        "jlpt_level": jlpt_level,
        "youtube_link": v1_data.get("youtube_link", ""),
        "in_db": v1_data.get("in_db", False),
        "ai_explanation": _build_ai_explanation_from_v1(v1_data),
        "jisho_data": _extract_jisho_data_from_v1(v1_data),
        "kanji_list": _extract_kanji_list(word),
        "kanji_data": _build_kanji_data_from_v1(v1_data),
        "collocations": _extract_collocations_from_v1(v1_data),
    }

    logger.info(f"✅ Successfully migrated word '{word}' to v0.2.0")
    return v2_data


def _extract_jlpt_level(jlpt_list: List[str]) -> int:
    """Extract numeric JLPT level from jlpt list"""
    if not jlpt_list:
        return 5  # Default to N5

    # Map JLPT strings to numbers
    jlpt_map = {"jlpt-n1": 1, "jlpt-n2": 2, "jlpt-n3": 3, "jlpt-n4": 4, "jlpt-n5": 5}

    # Find the highest level (lowest number)
    levels = [jlpt_map.get(jlpt, 5) for jlpt in jlpt_list if jlpt in jlpt_map]
    return min(levels) if levels else 5


def _build_ai_explanation_from_v1(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build ai_explanation object from v0.1.1 data"""
    word = v1_data.get("word", "")
    reading = v1_data.get("reading", "")
    meanings = v1_data.get("meanings", [])
    explanations = v1_data.get("explanations", {})
    examples = v1_data.get("examples", [])
    synonyms = v1_data.get("synonyms", [])
    antonyms = v1_data.get("antonyms", [])

    ai_explanation = {
        "kanji": word,
        "reading": reading or word,
    }

    # Add explanations if available
    if explanations:
        ai_explanation.update(
            {
                "introduction_japanese": "",  # Not available in v0.1.1
                "introduction_english": explanations.get("motivation", ""),
                "meaning_explanation_japanese": "",  # Not available in v0.1.1
                "meaning_explanation_english": explanations.get("explanation", ""),
                "kanji_explanation_english": explanations.get(
                    "kanji_explanation", "This word is usually written in kana, so there are no kanji to explain."
                ),
            }
        )

    # Convert meanings
    if meanings:
        meaning_groups = []
        meaning_translations = {}

        for meaning in meanings:
            if meaning.get("neuances"):
                primary_meaning = meaning["neuances"][0]
                meaning_groups.append(meaning["neuances"])

                # Convert translation object to v0.2.0 format
                if meaning.get("translation"):
                    translations = _convert_translation_to_v2(meaning["translation"])
                    meaning_translations[primary_meaning] = translations

        ai_explanation["meanings"] = meaning_groups
        ai_explanation["meaning_translations"] = meaning_translations

    # Convert examples
    if examples:
        converted_examples = []
        for example in examples:
            converted_example = {
                "kanji": example.get("kanji", ""),
                "furigana": example.get("furigana", ""),
            }

            # Convert translation
            if example.get("translation"):
                converted_example["translations"] = _convert_translation_to_v2(example["translation"])

            converted_examples.append(converted_example)

        ai_explanation["examples"] = converted_examples

    # Convert synonyms and antonyms
    if synonyms:
        ai_explanation["synonyms"] = [
            f"{syn.get('word', '')} : {syn.get('reading', '')} : {_get_first_meaning(syn)}"
            for syn in synonyms
            if syn.get("word")
        ]
        ai_explanation["synonyms_explanation"] = explanations.get("synonyms_explanation", "")

    if antonyms:
        ai_explanation["antonyms"] = [
            f"{ant.get('word', '')} : {ant.get('reading', '')} : {_get_first_meaning(ant)}"
            for ant in antonyms
            if ant.get("word")
        ]
        ai_explanation["antonyms_explanation"] = explanations.get("antonyms_explanation", "")

    # Add kanji details if available
    kanjis = v1_data.get("kanjis", [])
    if kanjis:
        kanji_details = []
        for kanji_obj in kanjis:
            kanji_detail = {"kanji": kanji_obj.get("kanji", ""), "common_words": []}

            # Extract common words from examples
            examples = kanji_obj.get("examples", [])
            for example in examples[:2]:  # Limit to 2 examples
                word = example.get("word", "")
                reading = example.get("reading", "")
                meaning = _get_first_meaning(example)
                if word and meaning:
                    kanji_detail["common_words"].append(f"{word}: {meaning}")

            kanji_details.append(kanji_detail)

        ai_explanation["kanji_details"] = kanji_details

    return ai_explanation


def _convert_translation_to_v2(v1_translation: Dict[str, str]) -> Dict[str, str]:
    """Convert v0.1.1 translation format to v0.2.0 format"""
    v2_translation = {}

    # Map v0.1.1 language names to v0.2.0 codes
    lang_mapping = {
        "English": "EN",
        "Persian": "FA",
        "Nepali": "NE",
        "Indonesian": "ID",
        "Filipino": "TL",
        "Vietnamese": "VI",
        "Burmese": "MY",
        "Korean": "KO",
        "Hindi": "HI",
        "Arabic": "AR",
        "French": "FR",
        "Spanish": "ES",
        "Chinese": "ZH",
        "Bengali": "BN",
    }

    for lang_name, text in v1_translation.items():
        if lang_name in lang_mapping and text:
            v2_translation[lang_mapping[lang_name]] = text

    # Sort by preference order
    order_list = ["EN", "ID", "ES", "VI", "FR", "NE", "BN", "ZH", "KO", "TL", "MY", "HI", "AR", "FA"]
    return {key: v2_translation[key] for key in order_list if key in v2_translation}


def _extract_jisho_data_from_v1(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract jisho_data equivalent from v0.1.1 format"""
    meanings = v1_data.get("meanings", [])
    word = v1_data.get("word", "")
    reading = v1_data.get("reading", "")

    # Build basic jisho_data structure
    jisho_data = {
        "slug": word,
        "is_common": v1_data.get("is_common", False),
        "tags": [],
        "jlpt": v1_data.get("jlpt", []),
        "japanese": [{"word": word, "reading": reading}] if reading else [{"word": word}],
        "senses": [],
    }

    # Convert meanings to senses
    for meaning in meanings:
        if meaning.get("neuances"):
            sense = {
                "english_definitions": meaning["neuances"],
                "parts_of_speech": [meaning.get("part_of_speech", "")],
                "links": [],
                "tags": [],
                "restrictions": [],
                "see_also": [],
                "antonyms": [],
                "source": [],
                "info": [],
            }
            jisho_data["senses"].append(sense)

    return jisho_data


def _extract_kanji_list(word: str) -> List[str]:
    """Extract kanji characters from word"""
    return re.findall(r"[\u4E00-\u9FFF]", word)


def _build_kanji_data_from_v1(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build kanji_data from v0.1.1 kanji information"""
    kanji_data = {}
    kanjis = v1_data.get("kanjis", [])

    for kanji_obj in kanjis:
        kanji = kanji_obj.get("kanji", "")
        if kanji:
            kanji_data[kanji] = {
                "meanings": kanji_obj.get("meanings", []),
                "on_readings": kanji_obj.get("onyomi", []),
                "kun_readings": kanji_obj.get("kunyomi", []),
                "stroke_count": kanji_obj.get("strokes"),
                "jlpt": kanji_obj.get("jlpt"),
                "freq_mainichi_shinbun": kanji_obj.get("frequency"),
                "unicode": kanji_obj.get("unicode"),
                "grade": kanji_obj.get("grade"),
            }

    return kanji_data


def _extract_collocations_from_v1(v1_data: Dict[str, Any]) -> List[str]:
    """Extract collocations from v0.1.1 explanations"""
    explanations = v1_data.get("explanations", {})
    return explanations.get("collocations", [])


def _get_first_meaning(word_obj: Dict[str, Any]) -> str:
    """Get first meaning from a word object"""
    meanings = word_obj.get("meanings", [])
    if meanings and meanings[0].get("neuances"):
        return meanings[0]["neuances"][0]
    return ""


def migrate_file(file_path: str) -> bool:
    """
    Migrate a single v0.1.1 JSON file to v0.2.0 format

    Args:
        file_path: Path to the v0.1.1 JSON file

    Returns:
        True if migration was successful, False otherwise
    """
    try:
        logger.info(f"🔄 Starting migration of file: {file_path}")

        # Read v0.1.1 file
        with open(file_path, "r", encoding="utf-8") as f:
            v1_data = json.load(f)

        # Check if already v0.2.0
        if v1_data.get("version", "").startswith("0.2"):
            logger.info(f"⏭️ File {file_path} is already v0.2.0, skipping")
            return True

        # Migrate to v0.2.0
        v2_data = migrate_word_v1_to_v2(v1_data)

        # Create backup
        backup_path = file_path + ".v0.1.1.backup"
        if not os.path.exists(backup_path):
            logger.info(f"💾 Creating backup: {backup_path}")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(v1_data, f, ensure_ascii=False, indent=4)

        # Write v0.2.0 file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(v2_data, f, ensure_ascii=False, indent=4)

        logger.info(f"✅ Successfully migrated file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to migrate file {file_path}: {e}")
        return False


def migrate_directory(directory_path: str) -> None:
    """
    Migrate all v0.1.1 JSON files in a directory to v0.2.0 format

    Args:
        directory_path: Path to directory containing JSON files
    """
    logger.info(f"🚀 Starting batch migration in directory: {directory_path}")

    directory = Path(directory_path)
    if not directory.exists():
        logger.error(f"❌ Directory does not exist: {directory_path}")
        return

    json_files = list(directory.glob("*.json"))
    if not json_files:
        logger.info(f"ℹ️ No JSON files found in {directory_path}")
        return

    success_count = 0
    total_count = len(json_files)

    for json_file in json_files:
        if migrate_file(str(json_file)):
            success_count += 1

    logger.info(f"🎉 Migration complete: {success_count}/{total_count} files migrated successfully")


def migrate_word_v2_to_v3(v2_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert JPWord v0.2.0 format to v0.3.0 format

    Args:
        v2_data: Word data in v0.2.0 format

    Returns:
        Word data in v0.3.0 format
    """
    logger.info(f"🔄 Migrating word '{v2_data.get('word', 'unknown')}' from v0.2.0 to v0.3.0")

    # Extract ai_explanation object
    ai_explanation = v2_data.get("ai_explanation", {})

    # Build v0.3.0 structure - flatten ai_explanation to top level
    v3_data = {
        "version": "0.3.0",
        "word": v2_data.get("word", ""),
        "jlpt_level": v2_data.get("jlpt_level", 5),
        "youtube_link": v2_data.get("youtube_link", ""),
        "in_db": v2_data.get("in_db", False),
        # Fields from ai_explanation moved to top level
        "kanji": ai_explanation.get("kanji", v2_data.get("word", "")),
        "reading": ai_explanation.get("reading", ""),
        "introduction_japanese": ai_explanation.get("introduction_japanese", ""),
        "introduction_english": ai_explanation.get("introduction_english", ""),
        "meanings": ai_explanation.get("meanings", []),
        "meaning_explanation_japanese": ai_explanation.get("meaning_explanation_japanese", ""),
        "meaning_explanation_english": ai_explanation.get("meaning_explanation_english", ""),
        "youtube_description": ai_explanation.get("youtube_description", ""),
        "kanji_details": ai_explanation.get("kanji_details", []),
        # Rename: kanji_explanation_english -> kanji_explanation
        "kanji_explanation": ai_explanation.get("kanji_explanation_english", ""),
        "synonyms": ai_explanation.get("synonyms", []),
        # Rename: synonyms_explanation -> synonym_explanation (singular)
        "synonym_explanation": ai_explanation.get("synonyms_explanation", ""),
        "antonyms": ai_explanation.get("antonyms", []),
        # Rename: antonyms_explanation -> antonym_explanation (singular)
        "antonym_explanation": ai_explanation.get("antonyms_explanation", ""),
        # Convert collocations from simple strings to JapaneseText objects
        "collocations": _convert_collocations_to_v3(v2_data.get("collocations", [])),
        # Rename: examples -> example_sentences
        "example_sentences": ai_explanation.get("examples", []),
        # meanings_translations moved to top level
        "meanings_translations": ai_explanation.get("meaning_translations", []),
        # Keep existing data
        "jisho_data": v2_data.get("jisho_data", {}),
        "kanji_list": v2_data.get("kanji_list", []),
        "kanji_data": v2_data.get("kanji_data", {}),
    }

    logger.info(f"✅ Successfully migrated word '{v2_data.get('word', '')}' to v0.3.0")
    return v3_data


def _convert_collocations_to_v3(collocations: List[Any]) -> List[Dict[str, Any]]:
    """
    Convert collocations from v0.2.0 format (list of strings) to v0.3.0 format (list of JapaneseText objects)

    Args:
        collocations: List of collocation strings or objects

    Returns:
        List of JapaneseText objects with kanji, furigana, and translations fields
    """
    converted = []

    for collocation in collocations:
        # If already an object (dict), keep it
        if isinstance(collocation, dict):
            # Ensure it has the required structure
            if "kanji" in collocation and "furigana" in collocation:
                if "translations" not in collocation:
                    collocation["translations"] = {}
                converted.append(collocation)
        # If it's a string, convert to object format
        elif isinstance(collocation, str):
            converted_collocation = {
                "kanji": collocation,
                "furigana": collocation,  # Default to same as kanji if no furigana available
                "translations": {},
            }
            converted.append(converted_collocation)

    return converted


def migrate_file_v2_to_v3(file_path: str) -> bool:
    """
    Migrate a single v0.2.0 JSON file to v0.3.0 format

    Args:
        file_path: Path to the v0.2.0 JSON file

    Returns:
        True if migration was successful, False otherwise
    """
    try:
        logger.info(f"🔄 Starting migration of file from v0.2.0 to v0.3.0: {file_path}")

        # Read v0.2.0 file
        with open(file_path, "r", encoding="utf-8") as f:
            v2_data = json.load(f)

        # Check version
        version = v2_data.get("version", "")
        if version.startswith("0.3"):
            logger.info(f"⏭️ File {file_path} is already v0.3.0, skipping")
            return True
        elif not version.startswith("0.2"):
            logger.warning(f"⚠️ File {file_path} is not v0.2.0 (version: {version}), skipping")
            return False

        # Migrate to v0.3.0
        v3_data = migrate_word_v2_to_v3(v2_data)

        # Create backup
        backup_path = file_path + ".v0.2.0.backup"
        if not os.path.exists(backup_path):
            logger.info(f"💾 Creating backup: {backup_path}")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(v2_data, f, ensure_ascii=False, indent=2)

        # Write v0.3.0 file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(v3_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Successfully migrated file to v0.3.0: {file_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to migrate file {file_path} to v0.3.0: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def migrate_directory_v2_to_v3(directory_path: str) -> None:
    """
    Migrate all v0.2.0 JSON files in a directory to v0.3.0 format

    Args:
        directory_path: Path to directory containing JSON files
    """
    logger.info(f"🚀 Starting batch migration v0.2.0 to v0.3.0 in directory: {directory_path}")

    directory = Path(directory_path)
    if not directory.exists():
        logger.error(f"❌ Directory does not exist: {directory_path}")
        return

    json_files = list(directory.glob("*.json"))
    if not json_files:
        logger.info(f"ℹ️ No JSON files found in {directory_path}")
        return

    success_count = 0
    total_count = len(json_files)

    for json_file in json_files:
        if migrate_file_v2_to_v3(str(json_file)):
            success_count += 1

    logger.info(f"🎉 Migration complete: {success_count}/{total_count} files migrated successfully")


def migrate_all_word_files() -> None:
    """Migrate all word files in the project"""
    # Migrate files in resources/words/
    resources_dir = "resources/words"
    if os.path.exists(resources_dir):
        logger.info(f"🔄 Migrating files in {resources_dir}")
        migrate_directory(resources_dir)

    # Migrate files in output directories
    output_dir = "Output"
    if os.path.exists(output_dir):
        logger.info(f"🔄 Migrating files in {output_dir}")
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                json_file = os.path.join(item_path, f"{item}.json")
                if os.path.exists(json_file):
                    migrate_file(json_file)


def migrate_all_word_files_v2_to_v3() -> None:
    """Migrate all word files in the project from v0.2.0 to v0.3.0"""
    # Migrate files in resources/words/
    resources_dir = "resources/words"
    if os.path.exists(resources_dir):
        logger.info(f"🔄 Migrating files in {resources_dir} from v0.2.0 to v0.3.0")
        migrate_directory_v2_to_v3(resources_dir)

    # Migrate files in output directories
    output_dir = "Output"
    if os.path.exists(output_dir):
        logger.info(f"🔄 Migrating files in {output_dir} from v0.2.0 to v0.3.0")
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if os.path.isdir(item_path):
                json_file = os.path.join(item_path, f"{item}.json")
                if os.path.exists(json_file):
                    migrate_file_v2_to_v3(json_file)


if __name__ == "__main__":
    # # Migrate single file
    #    python -m src.word.migrate --file resources/words/不安.json --version v2-to-v3

    # # Migrate directory
    #    python -m src.word.migrate --directory resources/words --version v2-to-v3

    # # Migrate all files
    #    python -m src.word.migrate --all --version v2-to-v3
    import argparse

    parser = argparse.ArgumentParser(description="Migrate JPWord files between versions")
    parser.add_argument("--file", help="Migrate a single file")
    parser.add_argument("--directory", help="Migrate all JSON files in a directory")
    parser.add_argument("--all", action="store_true", help="Migrate all word files in the project")
    parser.add_argument(
        "--version",
        choices=["v1-to-v2", "v2-to-v3"],
        default="v1-to-v2",
        help="Migration version path (default: v1-to-v2)",
    )

    args = parser.parse_args()

    if args.version == "v2-to-v3":
        # v0.2.0 to v0.3.0 migration
        if args.file:
            migrate_file_v2_to_v3(args.file)
        elif args.directory:
            migrate_directory_v2_to_v3(args.directory)
        elif args.all:
            migrate_all_word_files_v2_to_v3()
        else:
            # Default: migrate resources/words directory
            migrate_directory_v2_to_v3("resources/words")
    else:
        # v0.1.1 to v0.2.0 migration (default)
        if args.file:
            migrate_file(args.file)
        elif args.directory:
            migrate_directory(args.directory)
        elif args.all:
            migrate_all_word_files()
        else:
            # Default: migrate resources/words directory
            migrate_directory("resources/words")
