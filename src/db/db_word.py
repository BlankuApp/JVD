import os
import sys
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import Client, create_client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

load_dotenv()

url: str = os.getenv("supabaseUrl")  # type: ignore
key: str = os.getenv("supabaseKey")  # type: ignore
supabase: Client = create_client(url, key)


def add_word(word: str, jlpt: int) -> bool:
    try:
        response = supabase.table("words").upsert({"word": word, "JLPT": jlpt}).execute()
        return bool(response.data)
    except Exception as _:
        return False


def get_words(jlpt: int | None = None) -> list[dict[str, str | int]]:
    try:
        if jlpt:
            response = supabase.table("words").select("*").eq("JLPT", jlpt).execute()
        else:
            response = supabase.table("words").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching words: {e}")
        return []


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


def get_due_card(auth: dict) -> dict:
    try:
        now = datetime.now(timezone.utc).isoformat()
        response = (
            supabase.table("user_card")
            .select("*")
            .eq("user_id", auth["id"])
            .eq("type", "JPWord")
            .lt("due", now)
            .order("due")
            .limit(1)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching user cards: {e}")
        return []


def get_due_cards_count(auth: dict) -> int:
    try:
        now = datetime.now(timezone.utc).isoformat()
        response = (
            supabase.table("user_card")
            .select("id", count="exact")
            .eq("user_id", auth["id"])
            .eq("type", "JPWord")
            .lt("due", now)
            .execute()
        )
        return response.count if response.count else 0
    except Exception as e:
        print(f"Error fetching user cards count: {e}")
        return 0


def update_user_word_card(
    auth: dict,
    word: str,
    state: str,
    step: int | None,
    stability: float | None,
    difficulty: float | None,
    due: str | None,
    last_review: str | None,
) -> tuple[bool, str]:
    try:
        data = {
            "state": state,
            "step": step,
            "stability": stability,
            "difficulty": difficulty,
            "due": due,
            "last_review": last_review,
        }
        response = (
            supabase.table("user_card")
            .update(data)
            .eq("user_id", auth["id"])
            .eq("key", word)
            .eq("type", "JPWord")
            .execute()
        )
        return bool(response.data), "Card updated successfully" if response.data else "Failed to update card"
    except Exception as e:
        print(f"Error updating user card: {e}")
        return False, "Error updating card"


if __name__ == "__main__":
    # Load JSON files
    vocabulary_files = [f[:-5] for f in os.listdir("resources/words") if f.endswith(".json")]
    vocabulary_files.sort()

    for file in vocabulary_files:
        with open(f"resources/words/{file}.json", "r", encoding="utf-8") as f:
            w = json.load(f)

        if not w["in_db"]:
            w["in_db"] = add_word(w["word"], w["jlpt_level"])
            w["in_db"] = True
            with open(f"resources/words/{file}.json", "w", encoding="utf-8") as f:
                json.dump(w, f, ensure_ascii=False, indent=4)
            print(f"Added {w['word']} to DB as JLPT N{w['jlpt_level']}")
