import os
from random import sample

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from src.word.JPWord import JPWord


@st.cache_data(ttl=3600)
def get_words() -> list[dict]:
    words = []
    json_files = [f for f in os.listdir("resources/words") if f.endswith(".json")]
    for json_file in json_files:
        with open(os.path.join("resources/words", json_file), "r", encoding="utf-8") as file:
            w = JPWord.model_validate_json(file.read())
            if w:
                words.append(dict(word=w.word, level=w.jlpt_level))
    return words


auth = st.session_state.get("auth", None)

if not auth:
    st.warning("You need to be logged in to access the review page.")
    st.stop()

load_dotenv()


client = OpenAI()

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


def get_questions(words: list[str], selected_levels: str):
    selected_words = [w["word"] for w in words if w["level"] in selected_levels]
    random_5_words = sample(selected_words, 5) if len(selected_words) >= 5 else None
    if random_5_words is None:
        st.warning("Please select at least 5 words from the chosen JLPT levels.")
        st.stop()
    prompt = """# Role
You are a Japanese teacher making fill-in-the-blank questions for each given word to challenge students' comprehension skills.
# Task
For each given word, do the following:
1. Make a random, relatively long, natural but grammatically a little bit difficult sentence with the word as 'full sentence'. Try to use the word in different conjugations and grammatical forms. The sentence must use only JLPT {{level}} and easier vocabularies.
2. Remove the conjugated word fully in its new form from the sentence and replace it with a blank (____) as the question in kanji as 'question'. The taken-out word (which is the conjugated form) should be the 'answer'.
3. As of 'hint', provide the same sentence as 'question' but with hiragana reading for each kanji in parentheses. For example, if the sentence is 日本語を勉強します, it should be 日本(にほん)語(ご)を勉強(べんきょう)します.

# JSON Output Format
Return the results in the following JSON format:
{
    "questions": [
    {
        "word": "string",
      "full_sentence": "string",
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
        result = eval(response.output_text)
        # st.json(result)
    except Exception:
        st.error("Failed to parse the response. Please try again.")
        st.stop()
    # # fmt: off
    # result = {"questions": [{"word": "眠い","full_sentence": "朝ご飯を食べて少し眠いです。","question": "朝ご飯を食べて少し____。","hint": "朝(あさ)ご飯(はん)を食(た)べて少(すこ)し____。","answer": "眠いです",},{"word": "平ら","full_sentence": "この机の上は平らで書きやすいです。","question": "この机の上は____で書きやすいです。","hint": "この机(つくえ)の上(うえ)は____で書(か)きやすいです。","answer": "平ら",},{"word": "入場","full_sentence": "チケットを見せてから入場してください。","question": "チケットを見せてから____してください。","hint": "チケットを見(み)せてから____してください。","answer": "入場",},{"word": "平ら","full_sentence": "この机の上は平らで書きやすいです。","question": "この机の上は____で書きやすいです。","hint": "この机(つくえ)の上(うえ)は____で書(か)きやすいです。","answer": "平ら",},{"word": "入場","full_sentence": "チケットを見せてから入場してください。","question": "チケットを見せてから____してください。","hint": "チケットを見(み)せてから____してください。","answer": "入場",},]}
    # # fmt: on
    st.session_state["comprehension_questions"] = result


if st.session_state.get("comprehension_questions", None) is None:
    get_questions(words, selected_levels)
result = st.session_state.get("comprehension_questions", None)
if result is None:
    st.error("Failed to get questions. Please try again.")
    st.stop()

st.text("Fill in the blanks with the correct form of the following words:")
with st.container(horizontal=True, border=True, horizontal_alignment="distribute"):
    random_5_words = [q.get("word", "") for q in result.get("questions", [])]
    for i, w in enumerate(random_5_words):
        st.markdown(f"**{w}**")

with st.form("comprehension_form", border=False, clear_on_submit=True):
    for i, q in enumerate(result.get("questions", [])):
        question = q.get("question", "")
        st.text(question)
        st.text_input(
            "Your Answer:",
            key=f"answer_{i}",
            placeholder="Type your answer here",
            autocomplete="off",
            label_visibility="collapsed",
        )

    submitted = st.form_submit_button("Check Answers", type="primary", use_container_width=True)

with st.expander("Hints", expanded=False):
    for i, q in enumerate(result.get("questions", [])):
        hint = q.get("hint", "")
        st.text(hint)

if submitted:
    correct_count = 0
    for i, q in enumerate(result.get("questions", [])):
        answer = q.get("answer", "")
        full_sentence = q.get("full_sentence", "")
        hint = q.get("hint", "")
        user_answer = st.session_state.get(f"answer_{i}", "").strip()
        if user_answer == answer:
            st.success(f"Question {i + 1}: Correct! 🎉")
            correct_count += 1
        else:
            st.error(f"Question {i + 1}: Incorrect. The correct answer is: {answer}")
        st.text(full_sentence)
        st.text(hint)
    if correct_count == len(result.get("questions", [])):
        st.balloons()
    st.info(f"You got {correct_count} out of {len(result.get('questions', []))} correct.")

if st.button("Generate New Questions", type="secondary", use_container_width=True):
    del st.session_state["comprehension_questions"]
    for i in range(len(result.get("questions", []))):
        if f"answer_{i}" in st.session_state:
            del st.session_state[f"answer_{i}"]
    st.rerun()
