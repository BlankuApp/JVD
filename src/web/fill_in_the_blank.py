import json
import os
from random import sample, shuffle

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from src.utils import create_html_with_ruby
from src.word.JPWord import JPWord


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
        result = eval(response.output_text)
    except Exception:
        st.error("Failed to parse the response. Please try again.")
        st.stop()
    # # fmt: off
    # result = {"questions": [{"word": "議長","full_sentence": "会議で様々な意見が出たが、最後に議長が冷静に全体の流れをまとめて結論を出した。","full_sentence_reading": "会議(かいぎ)で様々(さまざま)な意見(いけん)が出(で)たが、最後(さいご)に議長(ぎちょう)が冷静(れいせい)に全体(ぜんたい)の流(なが)れをまとめて結論(けつろん)を出(だ)した。","question": "会議で様々な意見が出たが、最後に____が冷静に全体の流れをまとめて結論を出した。","hint": "会議(かいぎ)で様々(さまざま)な意見(いけん)が出(で)たが、最後(さいご)に____が冷静(れいせい)に全体(ぜ んたい)の流(なが)れをまとめて結論(けつろん)を出(だ)した。","answer": "議長"},{"word": "博士","full_sentence": "彼は長年の研究で新しい理論を証明して、ついに博士の学位を受け取ることができた。","full_sentence_reading": "彼(かれ)は長年(ながねん)の研究(けんきゅう)で新(あたら)しい理論(りろん)を証明(しょうめい)して、ついに博士(はくし)の学位(がくい)を受(う)け取(と)ることができた。","question": "彼は長年の研究で新しい理論を証明して、ついに____の学位を受け取ることができた。","hint": "彼(かれ)は長年(ながねん)の研究(けんきゅう)で新(あたら)しい理論(りろん)を証明(しょうめい)して、ついに____の学位(がくい)を受(う)け取(と)ることができた。","answer": "博士"},{"word": "割れる","full_sentence": "地震の強い揺れで窓ガラスが突然大きく割れて、家の中に細かい破片が飛び散った。","full_sentence_reading": "地震(じしん)の強(つよ)い揺(ゆ)れで窓(まど)ガラスが突然(とつぜん)大(おお)きく割(わ) れて、家(いえ)の中(なか)に細(こま)かい破片(はへん)が飛(と)び散(ち)った。","question": "地震の強い揺れで窓ガラスが突然大きく____、家の中に細かい破片が飛び散った。","hint": "地震(じしん)の強(つよ)い揺(ゆ)れで窓(まど)ガラスが突然(とつぜん)大(おお)きく____、家(いえ)の中(なか)に細(こま)かい破片(はへん)が飛(と)び散(ち)った。","answer": "割れて"},{"word": "加える","full_sentence": "料理が少し味気ないと感じたので、最後に塩と少しのしょうゆを加えて味を整えた。","full_sentence_reading": "料理(りょうり)が少(すこ)し味気(あじけ)ないと感(かん)じたので、最後(さいご)に塩(しお)と少(すこ)しのしょうゆを加(くわ)えて味(あじ)を整(ととの)えた。","question": "料理が少し味気ないと感じたので、最後に塩と少しのしょうゆを____味を整えた。","hint": "料理(りょうり)が少(すこ)し味気(あじけ)ないと感(かん)じたので、最後(さいご)に塩(しお)と少(すこ)しのしょうゆを____味(あじ)を整(ととの)えた。","answer": "加えて"},{"word": "従う","full_sentence": "旅行先で現地のルールや案内に従わなければ、思わぬトラブルに巻き込まれることがある。",       "full_sentence_reading": "旅行先(りょこうさき)で現地(げんち)のルールや案内(あんない)に従(したが)わなければ、 思(おも)わぬトラブルに巻(ま)き込(こ)まれることがある。","question": "旅行先で現地のルールや案内に____、思わぬトラブルに巻き込まれることがある。","hint": "旅行先(りょこうさき)で現地(げんち)のルールや案内(あんない)に____、思(おも)わぬトラブルに巻(ま)き込( こ)まれることがある。","answer": "従わなければ"}]}
    # # fmt: on
    st.session_state["comprehension_questions"] = result


result = st.session_state.get("comprehension_questions", None)
if result is None:
    if st.button("Generate Questions", type="primary", use_container_width=True):
        get_questions(words, selected_levels)
        st.rerun()
else:
    st.text("Fill in the blanks with the correct form of the following words:")

    with st.form("comprehension_form", border=False, clear_on_submit=False):
        answers = [x.get("answer", "") for x in result.get("questions", [])]
        shuffle(answers)
        for i, q in enumerate(result.get("questions", [])):
            question = q.get("question", "")
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
            st.divider()
        submitted = st.form_submit_button("Check Answers", type="primary", use_container_width=True)

    if submitted:
        correct_count = 0
        for i, q in enumerate(result.get("questions", [])):
            answer = q.get("answer", "")
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
        if correct_count == len(result.get("questions", [])):
            st.balloons()
        st.info(f"You got {correct_count} out of {len(result.get('questions', []))} correct.")

    if st.button("Generate New Questions", type="secondary", use_container_width=True):
        del st.session_state["comprehension_questions"]
        for i in range(len(result.get("questions", []))):
            if f"answer_{i}" in st.session_state:
                del st.session_state[f"answer_{i}"]
        get_questions(words, selected_levels)
        st.rerun()
