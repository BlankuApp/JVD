import json
import os
from random import sample, shuffle

import streamlit as st
from dotenv import load_dotenv

from src import LANGUAGES_ABBR, get_openai_client
from src.utils import create_html_with_ruby
from src.word.JPWord import JPWord
from src.word.JPWord2 import translate_text


@st.cache_data(ttl=3600)
def get_words() -> list[dict]:
    words = []
    json_files = [f for f in os.listdir("resources/words") if f.endswith(".json")]
    for json_file in json_files:
        with open(os.path.join("resources/words", json_file), "r", encoding="utf-8") as file:
            raw_data = file.read()
            json_data = json.loads(raw_data)
            version = json_data.get("version")
            w = None
            if version == "0.1.1":
                w = JPWord.model_validate_json(raw_data)
                words.append(dict(word=w.word, level=w.jlpt_level))
            if version == "0.2.0":
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
)
selected_levels = [int(ll[1]) for ll in selection]


def get_questions(words: list[dict], selected_levels: list[int]) -> None:
    selected_words = [w["word"] for w in words if w["level"] in selected_levels]
    random_5_words = sample(selected_words, 5) if len(selected_words) >= 5 else None
    if random_5_words is None:
        st.toast("⚠️ Please select at least 5 words from the chosen JLPT levels.", icon="⚠️")
        st.stop()
    prompt = """# Role
You are a Japanese teacher making fill-in-the-blank questions for each given word to challenge students' comprehension skills.
# Task
For each given word, do the following:
1. Make a random, relatively long, natural but grammatically a little bit difficult sentence with the word as 'full sentence'. Try to use the word in different conjugations and grammatical forms. The sentence must use only JLPT {{level}} and easier vocabularies.
2. Remove the conjugated word fully in its new form from the sentence and replace it with a blank (____) as the question in kanji as 'question'. The taken-out word (which is the conjugated form) should be the 'answer'.
3. As of 'hint', provide the same sentence as 'question' but with hiragana reading for each kanji in parentheses. For example, if the sentence is 日本語を勉強します, it should be 日本(にほん)語(ご)を勉強(べんきょう)します.
4. As of 'full_sentence_reading', provide the same sentence as 'full sentence' but with hiragana reading for each kanji in parentheses.

# JSON Output Format
Return the results in the following JSON format:
{
    "questions": [
    {
        "word": "string",
      "full_sentence": "string",
      "full_sentence_reading": "string",
      "question": "string",
      "hint": "string",
      "answer": "string"
    },
    ...
  ]
}
# Example
For the word '叩く', the output should be:
{
    "questions": [
    {
      "word": "叩く",
      "full_sentence": "彼女は古いドアの音が気になって、何度も軽くドアを叩いて確かめた。",
      "full_sentence_reading": "彼女(かのじょ)は古(ふる)いドアの音(おと)が気(き)になって、何度(なんど)も軽(かる)くドアを叩(たた)いて確(たし)かめた。",
      "question": "彼女は古いドアの音が気になって、何度も軽くドアを____確かめた。",
      "hint": "彼女(かのじょ)は古(ふる)いドアの音(おと)が気(き)になって、何度(なんど)も軽(かる)くドアを____確(たし)かめた。",
      "answer": "叩いて"
    }
  ]
}
"""
    prompt = prompt.replace("{{level}}", "N" + str(min(selected_levels)))
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
        st.toast("✅ Questions generated successfully!", icon="✅")
    except json.JSONDecodeError:
        st.toast("❌ Failed to parse AI response. Please try again.", icon="❌")
        st.stop()

    st.session_state["comprehension_questions"] = result


result = st.session_state.get("comprehension_questions", None)
if result is None:
    if st.button("Generate Questions", type="primary", use_container_width=True):
        get_questions(words, selected_levels)
        st.rerun()
else:
    # Check if answers have been submitted
    answers_submitted = st.session_state.get("answers_submitted", False)

    if not answers_submitted:
        st.text("Fill in the blanks with the proper choices:")

        with st.form("comprehension_form", border=False, clear_on_submit=False):
            answers = [x.get("answer", "") for x in result.get("questions", [])]
            shuffle(answers)
            for i, q in enumerate(result.get("questions", [])):
                question = q.get("question", "")
                with st.container(border=True):  # Add border for consistency
                    with st.container(border=False, horizontal=True, vertical_alignment="bottom"):
                        st.markdown(
                            f"<span style='font-size:1.0rem'>{question}</span>", unsafe_allow_html=True, width="content"
                        )
                        st.segmented_control(
                            label="Select your answer",
                            options=answers,
                            key=f"answer_{i}",
                            default=st.session_state.get(f"answer_{i}", None),
                            label_visibility="collapsed",
                        )
                        with st.popover("Furigana"):
                            ruby = create_html_with_ruby(q.get("hint", ""))
                            st.markdown(ruby, unsafe_allow_html=True)
            submitted = st.form_submit_button("Check Answers", type="primary", use_container_width=True)

        if submitted:
            st.session_state["answers_submitted"] = True
            st.rerun()

    if answers_submitted:
        correct_count = 0
        for i, q in enumerate(result.get("questions", [])):
            answer = q.get("answer", "")
            full_sentence = q.get("full_sentence", "")
            full_sentence_reading = q.get("full_sentence_reading", "")
            hint = q.get("hint", "")
            user_answer = st.session_state.get(f"answer_{i}", "")
            if user_answer == answer:
                st.success(f"Question {i + 1}: Correct! 🎉")
                correct_count += 1
            else:
                st.error(f"Question {i + 1}: Incorrect. The correct answer is: {answer}")
            ruby = create_html_with_ruby(full_sentence_reading)
            st.markdown(ruby, unsafe_allow_html=True)
            user_langs = [LANGUAGES_ABBR[lang] for lang in auth.get("preferred_languages", [])]
            for lang in user_langs:
                translation = translate_text(full_sentence, target_language=lang, source_language="JA")
                st.markdown(f"**{lang}:** {translation}")
        if correct_count == len(result.get("questions", [])):
            st.balloons()
        st.info(f"You got {correct_count} out of {len(result.get('questions', []))} correct.")

    if st.button("Generate New Questions", type="secondary", use_container_width=True):
        # Clean up all related session state
        keys_to_remove = ["comprehension_questions", "answers_submitted"]
        keys_to_remove.extend([f"answer_{i}" for i in range(len(result.get("questions", [])))])

        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]

        get_questions(words, selected_levels)
        st.rerun()
