import json
import os
from random import sample, shuffle

import streamlit as st

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
            words.append(dict(word=json_data["word"], level=json_data["jlpt_level"]))
    return words


state = st.session_state.get("fill_in_the_blank_state", "Initial")

auth = st.session_state.get("auth", None)

if not auth:
    st.switch_page("src/web/user.py")

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
placeholder = st.empty()


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

    # # fmt: off
    # with st.spinner("Generating questions with AI (Usually takes 20-30 seconds)...", show_time=True):
    #     # Simulate a delay for demonstration purposes
    #     import time
    #     time.sleep(3)
    #     result = {"questions":[{"word":"丸い","full_sentence":"子どもは砂場で丸い石を見つけて大事にポケットに入れ、家に帰ってからもいつも眺めていた。","full_sentence_reading":"子(こ)どもは砂場(すなば)で丸(まる)い石(いし)を見(み)つけて大事(だいじ)にポケットに入(い)れ、家(いえ)に帰(かえ)ってからもいつも眺(なが)めていた。","question":"子どもは砂場で____石を見つけて大事にポケットに入れ、家に帰ってからもいつも眺めていた。","hint":"子(こ)どもは砂場(すなば)で____石(いし)を見(み)つけて大事(だいじ)にポケットに入(い)れ、家(いえ)に帰(かえ)ってからもいつも眺(なが)めていた。","answer":"丸い"},{"word":"計算","full_sentence":"彼は毎晩家計を正しくつけるために電卓を使って細かく計算して、無駄な出費を減らそうとしている。","full_sentence_reading":"彼(かれ)は毎晩(まいばん)家計(かけい)を正(ただ)しくつけるために電卓(でんたく)を使(つか)って細(こま)かく計算(けいさん)して、無駄(むだ)な出費(しゅっぴ)を減(へ)らそうとしている。","question":"彼は毎晩家計を正しくつけるために電卓を使って細かく____して、無駄な出費を減らそうとしている。","hint":"彼(かれ)は毎晩(まいばん)家計(かけい)を正(ただ)しくつけるために電卓(でんたく)を使(つか)って細(こま)かく____して、無駄(むだ)な出費(しゅっぴ)を減(へ)らそうとしている。","answer":"計算して"},{"word":"見事","full_sentence":"彼女は大きな失敗の後でも努力を続け、最後には見事な発表をして皆の拍手を浴びた。","full_sentence_reading":"彼女(かのじょ)は大(おお)きな失敗(しっぱい)の後(あと)でも努力(どりょく)を続(つづ)け、最後(さいご)には見事(みごと)な発表(はっぴょう)をして皆(みな)の拍手(はくしゅ)を浴(あ)びた。","question":"彼女は大きな失敗の後でも努力を続け、最後には____な発表をして皆の拍手を浴びた。","hint":"彼女(かのじょ)は大(おお)きな失敗(しっぱい)の後(あと)でも努力(どりょく)を続(つづ)け、最後(さいご)には____な発表(はっぴょう)をして皆(みな)の拍手(はくしゅ)を浴(あ)びた。","answer":"見事"},{"word":"皮","full_sentence":"母は果物の皮をきれいにむいて小さな袋に入れ、あとでジャムを作るために冷蔵庫に保存した。","full_sentence_reading":"母(はは)は果物(くだもの)の皮(かわ)をきれいにむいて小(ちい)さな袋(ふくろ)に入(い)れ、あとでジャムを作(つく)るために冷蔵庫(れいぞうこ)に保存(ほぞん)した。","question":"母は果物の____をきれいにむいて小さな袋に入れ、あとでジャムを作るために冷蔵庫に保存した。","hint":"母(はは)は果物(くだもの)の____をきれいにむいて小(ちい)さな袋(ふくろ)に入(い)れ、あとでジャムを作(つく)るために冷蔵庫(れいぞうこ)に保存(ほぞん)した。","answer":"皮"},{"word":"揺れる","full_sentence":"夜中の強い風で窓のカーテンが大きく揺れて、その音で眠れなくなった人が何度も起きた。","full_sentence_reading":"夜中(よなか)の強(つよ)い風(かぜ)で窓(まど)のカーテンが大(おお)きく揺(ゆ)れて、その音(おと)で眠(ねむ)れなくなった人(ひと)が何度(なんど)も起(お)きた。","question":"夜中の強い風で窓のカーテンが大きく____、その音で眠れなくなった人が何度も起きた。","hint":"夜中(よなか)の強(つよ)い風(かぜ)で窓(まど)のカーテンが大(おお)きく____、その音(おと)で眠(ねむ)れなくなった人(ひと)が何度(なんど)も起(お)きた。","answer":"揺れて"}]}
    # # fmt: on
    st.session_state.update({"comprehension_questions": result, "fill_in_the_blank_state": "QuestionsGenerated"})
    st.rerun()


if state == "Initial":
    if placeholder.button("Generate Questions", type="primary", use_container_width=True):
        get_questions(words, selected_levels)
elif state == "QuestionsGenerated":
    with placeholder.container():
        st.text("Fill in the blanks with the proper choices:")
        result = st.session_state.comprehension_questions
        with st.form("comprehension_form", border=False, clear_on_submit=False):
            answers = [x.get("answer", "") for x in result.get("questions", [])]
            shuffle(answers)
            for i, q in enumerate(result.get("questions", [])):
                question = q.get("question", "")
                with st.container(border=True):  # Add border for consistency
                    with st.container(border=False, horizontal=True, horizontal_alignment="distribute"):
                        st.markdown(f"<span style='font-size:1.0rem'>{question}</span>", unsafe_allow_html=True)
                        st.radio(
                            label="Select your answer",
                            options=answers,
                            key=f"answer_{i}",
                            index=answers.index(st.session_state.get(f"answer_{i}", answers[0]))
                            if st.session_state.get(f"answer_{i}", None) in answers
                            else 0,
                            label_visibility="collapsed",
                            horizontal=True,
                        )
                        with st.popover("Furigana"):
                            ruby = create_html_with_ruby(q.get("hint", ""))
                            st.markdown(ruby, unsafe_allow_html=True)
            if st.form_submit_button("Check Answers", type="primary", use_container_width=True):
                st.session_state.fill_in_the_blank_state = "QuestionsAnswered"
                placeholder.empty()
                st.rerun()
elif state == "QuestionsAnswered":
    with placeholder.container():
        correct_count = 0
        result = st.session_state.comprehension_questions
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

        if st.button("Generate New Questions", type="secondary", use_container_width=True):
            st.session_state.fill_in_the_blank_state = "GeneratingNewQuestions"
            placeholder.empty()
            st.rerun()
elif state == "GeneratingNewQuestions":
    with placeholder.container():
        get_questions(words, selected_levels)
