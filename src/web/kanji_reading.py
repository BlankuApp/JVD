import json
import os
from random import sample, shuffle

import streamlit as st
from dotenv import load_dotenv

from src import LANGUAGES_ABBR, get_openai_client
from src.utils import create_html_with_ruby
from src.word.JPWord import translate_text


@st.cache_data(ttl=3600)
def get_words() -> list[dict]:
    words = []
    json_files = [f for f in os.listdir("resources/words") if f.endswith(".json")]
    for json_file in json_files:
        with open(os.path.join("resources/words", json_file), "r", encoding="utf-8") as file:
            raw_data = file.read()
            json_data = json.loads(raw_data)
            if len(json_data.get("kanji_list", [])) > 0:
                words.append(dict(word=json_data["word"], level=json_data["jlpt_level"]))
    return words


auth = st.session_state.get("auth", None)

if not auth:
    st.switch_page("src/web/user.py")

load_dotenv()

client = get_openai_client()

words = get_words()
word_levels = ["N5", "N4", "N3", "N2", "N1"]
selection = st.segmented_control(
    label="JLPT Level",
    options=word_levels,
    key="comprehension_level",
    selection_mode="multi",
    default=["N5", "N4", "N3"],
    label_visibility="collapsed",
    width="stretch",
)
selected_levels = [int(ll[1]) for ll in selection]


def get_questions(words: list[dict], selected_levels: list[int]) -> None:
    selected_words = [w["word"] for w in words if w["level"] in selected_levels]
    random_5_words = sample(selected_words, 5) if len(selected_words) >= 5 else None
    if random_5_words is None:
        st.toast("⚠️ Please select at least 5 words from the chosen JLPT levels.", icon="⚠️")
        st.stop()
    prompt = """# Role
        You are a Japanese reading quiz generator.
Your task: given a kanji words, create a multiple-choice question for each word that asks for the correct hiragana reading.
# Output format (strict)
Return only this JSON object, no extra text:
{
  "questions": [
    {
      "word": "<kanji word>",
      "correct_answer": "<correct hiragana reading>",
      "choices": ["<a>", "<b>", "<c>", "<d>"],
      "explanation_ja": "<short Japanese explanation>",
      "explanation_en": "<one-sentence English tip>",
      "notes": "<edge cases / frequency if relevant>"
    }, ...
  ]
}
}

# Rules:
choices: 4 items, hiragana only, no kanji/katakana/romaji.
Exactly one correct answer. Put it at index 0, then shuffle the remaining 3 before output. (Do not reshuffle index 0.)
Keep all choices the same script and length-ish (within ±2 mora).
Avoid repeated identical strings.
Question writing rules
Target: reading of the whole word (not per character).
Difficulty: choices must be close and challenging. Use these distractor patterns (pick 2–3 different ones each time):
- Vowel length: 長音／撥音 changes (e.g., こう vs こー, おう vs おお, ん insertion).
- Yōon small-ゃゅょ vs big-やゆよ (きょう vs きよう).
- Gemination: small っ vs つ (きって vs きつて).
- Dakuten: ひ vs び／ぴ (rendaku traps).
- On/kun mixups: swap to the other common reading type (学生 がくせい vs がくしょう).
- Okurigana habits: 行う おこなう vs misreadings (いく, おこないます→base おこなう).
- Common alt readings: 今日 きょう vs こんにち vs (classical けふ—mark as archaic in notes if used).
- Pitch-accent neutral: do not include accent marks; focus on spelling only.
- Register/frequency: If a distractor is archaic/rare, you may use it once, but add a short note in notes.
- Ambiguity: If the word genuinely has multiple equally valid readings in the same sense, pick the most common modern reading and explain in notes why others aren’t correct for this usage.

No furigana, no romaji in choices.
No gloss/meaning in the question—this is purely a reading task.

# Validation checklist (apply before output)
The question is kanji (may include kana okurigana as in 行う).
Only one correct reading exists for the intended sense.
All distractors differ by one small feature (length, dakuten, small っ/ゃゅょ, on/kun switch, rendaku).
All choices are non-identical and plausible.

# Examples to emulate (style, not content)
(These are examples—you should generate new content for new inputs.)

## Input: 学生
JSON Output:

{
  "question": "学生",
  "correct_answer": "がくせい",
  "choices": ["がくせい", "がくしょう", "がくせ", "かくせい"],
  "explanation_ja": "「学生」は音読みで「がくせい」。『生』を「しょう」と読むのは別語（例：一生）で本語では不適。",
  "explanation_en": "Use on’yomi for this compound; '生' is -せい here, not -しょう.",
  "notes": ""
}


## Input: 今日

{
  "question": "今日",
  "correct_answer": "きょう",
  "choices": ["きょう", "こんにち", "きよう", "けふ"],
  "explanation_ja": "日常語では「きょう」が最も一般的。『こんにち』は語義が異なり『けふ』は古語。",
  "explanation_en": "Modern everyday reading is きょう; こんにち is a different meaning; けふ is archaic.",
  "notes": "Multiple readings exist; this asks for the common 'today' reading."
}


## Input: 行う

{
  "question": "行う",
  "correct_answer": "おこなう",
  "choices": ["おこなう", "いく", "おこないます", "おかなう"],
  "explanation_ja": "「行う」は動詞基本形で「おこなう」。『いく』は別語、『おこないます』は丁寧形。",
  "explanation_en": "Base dictionary form is おこなう; いく is a different verb; おこないます is polite form.",
  "notes": ""
}


## Input: 一日（= ついたち の意）

{
  "question": "一日",
  "correct_answer": "ついたち",
  "choices": ["ついたち", "いちにち", "いちにちい", "ついだち"],
  "explanation_ja": "日付『1日』は「ついたち」。『いちにち』は時間量を表す別読み。",
  "explanation_en": "For calendar day 1, read ついたち; いちにち means 'one day (duration)'.",
  "notes": "Sense disambiguation included."
}


## Input: 大人

{
  "question": "大人",
  "correct_answer": "おとな",
  "choices": ["おとな", "だいにん", "おとにん", "おおとな"],
  "explanation_ja": "熟字訓で「おとな」。音読みの『だい』『にん』にはならない。",
  "explanation_en": "This is a jukujikun: read as おとな, not on’yomi parts.",
  "notes": "Jukujikun warning."
}
"""
    with st.spinner("Generating questions with AI (Usually takes 20-30 seconds)...", show_time=True):
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "developer", "content": [{"type": "input_text", "text": prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": str(random_5_words)}]},
            ],
            text={"format": {"type": "json_object"}, "verbosity": "medium"},
            reasoning={"effort": "minimal", "summary": None},
            tools=[],
            store=False,
            include=["reasoning.encrypted_content", "web_search_call.action.sources"],
        )
        try:
            result = json.loads(response.output_text)
            st.session_state["kanji_reading_questions"] = result
            st.toast("✅ Questions generated successfully!", icon="✅")
        except json.JSONDecodeError:
            st.toast("❌ Failed to parse AI response. Please try again.", icon="❌")
            st.stop()

    # fmt: off
    # st.session_state["kanji_reading_questions"] = {"questions":[{"word":"集まり","correct_answer":"あつまり","choices":["つどい","あつまり","あつまり","あつまる"],"explanation_ja":"「集まり」は名詞の形で「あつまり」。動詞なら「あつまる／あつめる」になる。","explanation_en":"As a noun meaning a gathering, the correct reading is あつまり; verbs use different forms.","notes":"Related verb forms exist (あつまる、あつめる); つどい is a synonym with different kanji (集い)."},{"word":"合図","correct_answer":"あいず","choices":["ごうず","あいず","あいずう","あいづ"],"explanation_ja":"「合図」は音読みで「あいず」。濁音や長音の間違いに注意。","explanation_en":"Modern reading is あいず; watch distractors with mistaken dakuten/length.","notes":""},{"word":"減る","correct_answer":"へる","choices":["へぇる","へる","げる","へらす"],"explanation_ja":"自動詞の『減る』は「へる」。他動詞は『減らす（へらす）』で形が変わる。","explanation_en":"As an intransitive verb meaning 'decrease', the reading is へる.","notes":"げる is not a valid reading here; watch similar-looking verbs."},{"word":"最も","correct_answer":"もっとも","choices":["もっとも","もっととも","さいもつ","もつとも"],"explanation_ja":"「最も」は副詞・形容詞用法で「もっとも」。音読みの組み合わせは別語になる。","explanation_en":"Common adverbial/relative reading is もっとも; on’yomi forms are not used here.","notes":"Choices include plausible mis-segmentations; もっとも is very frequent."},{"word":"休暇","correct_answer":"きゅうか","choices":["やすみ","やすみか","きゅうか","きゅうが"],"explanation_ja":"「休暇」は音読みで「きゅうか」。『やすみ』は同義語だが漢字語としては別読み。","explanation_en":"The Sino-Japanese reading is きゅうか; やすみ is a native alternative but not this compound reading.","notes":"Both readings relate to 'rest', but きゅうか is the standard compound reading for leave/holiday."}]}
    # fmt: on


result = st.session_state.get("kanji_reading_questions", None)

# Check if auto-generation is requested
if st.session_state.get("auto_generate_kanji_quiz", False):
    # Clear the flag to prevent infinite loop
    del st.session_state["auto_generate_kanji_quiz"]
    # Generate new questions automatically
    get_questions(words, selected_levels)
    st.rerun()

if result is None:
    if st.button("Generate Questions", type="primary", use_container_width=True):
        get_questions(words, selected_levels)
        st.rerun()
else:
    # Check if answers have been submitted
    answers_submitted = st.session_state.get("answers_submitted", False)

    if not answers_submitted:
        st.write("Select the correct hiragana reading for each kanji word.")

        # Generate shuffled choices once and store them in session state
        if "shuffled_choices" not in st.session_state:
            shuffled_choices = []
            for q in result["questions"]:
                choices = q["choices"].copy()
                shuffle(choices)
                shuffled_choices.append(choices)
            st.session_state["shuffled_choices"] = shuffled_choices

        with st.form("quiz_form", border=False):
            for idx, q in enumerate(result["questions"]):
                choices = st.session_state["shuffled_choices"][idx]
                st.markdown(f"<span style='font-size:1.5rem'>{q['word']}</span>", unsafe_allow_html=True)

                # Get the current selection from session state, default to None
                current_selection = st.session_state.get(f"question_{idx}", None)
                default_index = choices.index(current_selection) if current_selection in choices else 0

                user_choice = st.radio(
                    label=f"{q['word']}",
                    options=choices,
                    index=default_index,
                    key=f"question_{idx}",
                    label_visibility="collapsed",
                    horizontal=True,
                )
            submitted = st.form_submit_button("Submit Answers", type="primary", use_container_width=True)
            if submitted:
                st.session_state["answers_submitted"] = True
                st.rerun()

    else:
        for idx, q in enumerate(result["questions"]):
            correct_answer = q["correct_answer"]
            user_answer = st.session_state.get(f"question_{idx}", None)
            if user_answer == correct_answer:
                answer_style = "background: #f8f9fa; border-left: 5px solid #007bff;"
            else:
                answer_style = "background: #f8f9fa; border-left: 5px solid #ff0500;"

            st.markdown(
                f"<div style='{answer_style} padding: 0.5rem; border-radius: 10px; margin-bottom: 1rem;'>"
                f"<a href='/v?w={q['word']}' style='color: inherit; text-decoration: none; font-size: 1.5rem;'>{q['word']}({q['correct_answer']})</a>"
                f"<div>{q['explanation_en']}</div>"
                f"<div>{q['explanation_ja']}</div>"
                f"<div style='margin-top: 0.5rem; font-style: italic; color: #6c757d;'>{q['notes']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        if st.button("Generate New Quiz", type="primary", use_container_width=True):
            # Clear all quiz-related session state
            for i in range(len(result["questions"])):
                if f"question_{i}" in st.session_state:
                    del st.session_state[f"question_{i}"]
            keys_to_remove = ["answers_submitted", "kanji_reading_questions", "shuffled_choices"]
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["auto_generate_kanji_quiz"] = True
            st.rerun()
