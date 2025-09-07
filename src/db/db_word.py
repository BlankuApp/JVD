from dotenv import load_dotenv
from supabase import create_client, Client
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.word.JPWord import JPWord

load_dotenv()

url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)


def add_word(word: str, jlpt: int) -> bool:
    try:
        response = supabase.table("words").upsert({"word": word, "JLPT": jlpt}).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error adding word: {e}")
        return False


def add_user_word_card(auth: dict, word: str) -> tuple[bool, str]:
    try:
        data = {
            "user_id": auth["id"],
            "type": "JPWord",
            "key": word,
        }
        response = supabase.table("user_card").upsert(data).execute()
        return bool(response.data), "Card added successfully" if response.data else "Failed to add card"
    except Exception as e:
        print(f"Error adding user card: {e}")
        return False, "Error adding card"


def remove_user_word_card(auth: dict, word: str) -> tuple[bool, str]:
    try:
        response = (
            supabase.table("user_card")
            .delete()
            .eq("user_id", auth["id"])
            .eq("key", word)
            .eq("type", "JPWord")
            .execute()
        )
        return bool(response.data), "Card removed successfully" if response.data else "Failed to remove card"
    except Exception as e:
        print(f"Error removing user card: {e}")
        return False, "Error removing card"


def check_user_word_card(auth: dict, word: str) -> bool:
    try:
        response = (
            supabase.table("user_card")
            .select("*")
            .eq("user_id", auth["id"])
            .eq("key", word)
            .eq("type", "JPWord")
            .execute()
        )
        return bool(response.data)
    except Exception as e:
        print(f"Error checking user card: {e}")
        return False


def get_user_word_cards(auth: dict) -> list[dict]:
    try:
        response = supabase.table("user_card").select("*").eq("user_id", auth["id"]).eq("type", "JPWord").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching user cards: {e}")
        return []


if __name__ == "__main__":
    # Load JSON files
    n3_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n3") if f.endswith(".json")]
    n3_vocabulary_files.sort()

    n2_vocabulary_files = [f[:-5] for f in os.listdir("resources/words/n2") if f.endswith(".json")]
    n2_vocabulary_files.sort()

    for file in n3_vocabulary_files:
        w = JPWord.model_validate_json(open(f"resources/words/n3/{file}.json", "r", encoding="utf-8").read())
        if not w.in_db:
            w.in_db = add_word(w.word, 3)
            print(f"Added {w.word} to DB")

    for file in n2_vocabulary_files:
        w = JPWord.model_validate_json(open(f"resources/words/n2/{file}.json", "r", encoding="utf-8").read())
        if not w.in_db:
            w.in_db = add_word(w.word, 2)
            print(f"Added {w.word} to DB")
