import json
import os
import re

import openai
import requests
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from pydub import AudioSegment
from rich.console import Console
from rich.status import Status
from src.utils import create_html_with_ruby

load_dotenv()

console = Console()
status = Status("Starting...", console=console)


LANGUAGES_ABBR = {
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


class JPTranslation(BaseModel):
    Japanese: str = Field(default="", description="The given Japanese text.")
    English: str = Field(default="", description="The exact English translation of the given Japanese text.")
    Persian: str = Field(default="", description="The exact Persian translation of the given Japanese text.")
    Nepali: str = Field(default="", description="The exact Nepali translation of the given Japanese text.")
    Indonesian: str = Field(default="", description="The exact Indonesian translation of the given Japanese text.")
    Filipino: str = Field(default="", description="The exact Filipino translation of the given Japanese text.")
    Vietnamese: str = Field(default="", description="The exact Vietnamese translation of the given Japanese text.")
    Burmese: str = Field(default="", description="The exact Burmese translation of the given Japanese text.")
    Korean: str = Field(default="", description="The exact Korean translation of the given Japanese text.")
    Hindi: str = Field(default="", description="The exact Hindi translation of the given Japanese text.")
    Arabic: str = Field(default="", description="The exact Arabic translation of the given Japanese text.")
    French: str = Field(default="", description="The exact French translation of the given Japanese text.")
    Spanish: str = Field(default="", description="The exact Spanish translation of the given Japanese text.")
    Chinese: str = Field(default="", description="The exact Chinese translation of the given Japanese text.")
    Bengali: str = Field(default="", description="The exact Bengali translation of the given Japanese text.")


class JPExample(BaseModel):
    kanji: str = Field(description="The example sentence in Kanji. Example: 私は学生です。")
    furigana: str = Field(
        description="Rewrite the Japanese sentence so that every kanji block is immediately followed by its hiragana reading in parentheses [kanji](hiragana). Example: 私(わたし)は学生(がくせい)です。"
    )
    difficulty: int = Field(description="The difficulty level of the collocation from JLPT N1 to JLPT N5 level.")
    translation: JPTranslation = Field(default=JPTranslation())

    def show_in_streamlit(self, st, auth: dict | None = None) -> None:
        with st.expander(self.kanji):
            ruby = create_html_with_ruby(self.furigana)
            st.markdown(f":blue-badge[JLPT N{self.difficulty}] {ruby}", unsafe_allow_html=True)
            for key, value in self.translation:
                if key == "Japanese":
                    continue
                if auth:
                    if key not in auth.get("preferred_languages", []):
                        continue
                st.markdown(f":gray-badge[{LANGUAGES_ABBR[key]}] {value}")


class JPWordMeaning(BaseModel):
    neuances: list[str] = Field(default=[])
    part_of_speech: str | None = Field(default=None)
    translation: JPTranslation | None = Field(default=None)

    def show_in_streamlit(self, st, auth: dict | None = None) -> None:
        with st.container(border=1, horizontal=True, gap="small"):
            for key, value in self.translation:
                if key == "Japanese":
                    continue
                if auth:
                    if key not in auth.get("preferred_languages", []):
                        continue
                st.markdown(f":gray-badge[{LANGUAGES_ABBR[key]}] {value}")


class JPWordExplanations(BaseModel):
    """
    # Role
    You are a helpful Japanese language learning assistant who teaches in English.
    """

    explanation: str = Field(
        default="",
        description="""Write in a natural, conversational English transcript of a teacher explaining the meanings found, provide a very short but comprehensive and concise definition of the vocabulary word in simple English.
1. Since it is a transcript, don't use bullet points, parenthesis, e.g. or anything similar.
2. In the explanation field only insert the hiragana for of Japanese vocabs. No kanjis.
3. Explanation starts with English phrases such as:  "The word [word] means ..."
4. Keep it very short but cover all the meanings found.
""",
    )
    youtube_description: str | None = Field(
        default=None,
        description="""Improve the following YouTube description for a video teaching the given vocabulary word in Japanese. Make it very short, engaging and informative, highlighting the key points that will be covered in the video.
template:
Learn how to use the Japanese word [vocabulary word in kanji] ([kana reading]) in everyday conversations!  
In this video, we'll explore its meanings, kanji breakdowns, and collocations to help you master this essential vocabulary.
Whether you're a beginner or looking to expand your Japanese skills, this video is perfect for you. Don't forget to like, comment, and subscribe for more language learning content!
""",
    )
    motivation: str = Field(
        default="",
        description="""1. Fill out and paraphrase the following template:
The word we'll be learning in this section is [vocabulary word in hiragana] which you will often hear in [provide the situations where the word is commonly used without mentioning the meaning of the word]. 
2. Make sure you randomly change the starting phrase to make it more engaging. (change "The word we'll be learning in this section is" to something else randomly)
""",
    )
    collocations: list[str] | None = Field(
        default=None,
        description="list the easy and simple phrases in which the word is used in different contexts and nuances (more than 4 phrases). Japanese phrase only with no extra explanations.",
    )
    synonyms: list[str] = Field(
        default=[],
        description="List the 1 (maximum 2) most commonly used synonym for the provided Japanese vocabulary word (no readings or any other extra text, perferebly in kanji). Excluding the original word.",
    )
    synonyms_explanation: str | None = Field(
        default=None,
        description="""provide the English transcription of a very short explanation about the synonyms listed, including their nuances and meanings. If there were no synonyms in the list, say \"No common synonyms found.\"
# Constraints
1. Only insert the hiragana for of Japanese vocabs. No kanjis.
2. Explanation starts with English phrases such as:  "The most common synonyms of the [word] [are/is] ..."
3. Very shortly explain the nuances of each synonym and antonym listed, and how they differ from the original word.
""",
    )
    antonyms: list[str] = Field(
        default=[],
        description="List the 1 (maximum 2) most commonly used antonyms for the provided Japanese vocabulary word (no readings or any other extra text, perferebly in kanji). Excluding the original word.",
    )
    antonyms_explanation: str | None = Field(
        default=None,
        description="""provide the English transcription of a very short explanation about the antonyms listed, including their nuances and meanings. If there were no antonyms in the list, say \"No common antonyms found.\"
# Constraints
1. Only insert the hiragana for of Japanese vocabs. No kanjis.
2. Explanation starts with English phrases such as:  "The most common antonyms of the [word] [are/is] ..."
3. Very shortly explain the nuances of each synonym and antonym listed, and how they differ from the original word.
""",
    )


class JPKanji(BaseModel):
    kanji: str = ""
    meanings: list[str] = []
    onyomi: list[str] = []
    kunyomi: list[str] = []
    strokes: int | None = None
    jlpt: int | None = None
    frequency: int | None = None
    unicode: str | None = None
    grade: int | None = Field(default=None)
    examples: list["JPWord"] = Field(default=[])
    original_word: str | None = Field(default=None, exclude=True)

    def model_post_init(self, __context) -> None:
        if self.meanings or self.onyomi or self.kunyomi:
            return
        res = self.query(self.kanji)
        self.meanings = res.get("meanings", [])
        self.onyomi = res.get("on_readings", [])
        self.kunyomi = res.get("kun_readings", [])
        self.strokes = res.get("stroke_count", None)
        self.jlpt = res.get("jlpt", None)
        self.frequency = res.get("freq_mainichi_shinbun", None)
        self.unicode = res.get("unicode", None)
        self.grade = res.get("grade", None)

    @staticmethod
    def query(kanji: str) -> dict:
        url = f"https://kanjiapi.dev/v1/kanji/{kanji}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data
            else:
                raise ValueError(f"No definitions found for kanji '{kanji}'.")
        else:
            raise Exception(f"Error fetching data from Jisho API: {response.status_code}")

    def show_in_streamlit(self, st, original_word: str = "") -> None:
        cont = st.container(border=1)
        col1, col2 = cont.columns([2, 4])
        with col1:
            st.image(
                f"https://raw.githubusercontent.com/KanjiVG/kanjivg/refs/heads/master/kanji/0{self.unicode.lower()}.svg",
                width="stretch",
            )
        with col2:
            st.markdown(f":gray-badge[Meaning] {', '.join(self.meanings)}")
            st.markdown(f":gray-badge[On-yomi] {', '.join(self.onyomi)}")
            st.markdown(f":gray-badge[Kun-yomi] {', '.join(self.kunyomi)}")
            st.markdown("---")
            for example in self.examples:
                if example.word == original_word:
                    continue
                st.markdown(f"**{example.word}** ({example.reading}) : {', '.join(example.meanings[0].neuances)}")


JLPT_LEVELS_MAP = {"jlpt-n5": 5, "jlpt-n4": 4, "jlpt-n3": 3, "jlpt-n2": 2, "jlpt-n1": 1}


class JPWord(BaseModel):
    version: str = "0.1.1"
    word: str
    youtube_link: str = ""
    in_db: bool = Field(default=False)
    reading: str | None = None
    meanings: list[JPWordMeaning] = []
    kanjis: list[JPKanji] = []
    kanji_explanation: str | None = None
    explanations: JPWordExplanations | None = None
    is_common: bool = False
    jlpt: list[str] = []
    llm: BaseChatModel | None = Field(default=None, exclude=True)
    kanji_breakdown: bool = Field(default=True, exclude=True)
    examples: list[JPExample] = Field(default=[])
    synonyms: list["JPWord"] = Field(default=[])
    antonyms: list["JPWord"] = Field(default=[])

    @property
    def jlpt_level(self) -> int:
        levels = [JLPT_LEVELS_MAP.get(level.lower(), 6) for level in self.jlpt]
        return max(levels) if levels else 6

    def model_post_init(self, __context) -> None:
        if self.meanings or self.kanjis or self.explanations:
            return
        self._get_meanings()
        if self.kanji_breakdown:
            status.update("Fetching kanji breakdown ...")
            self._kanji_breakdown()
        self._get_examples()

    def _get_meanings(self) -> None:
        status.update("Fetching meanings from Jisho")
        res = self.query_jisho(self.word)
        if not res:
            status.update(f"No definitions found for word '{self.word}'.")
            return
        self.word = res[0].get("slug", self.word)
        self.is_common = res[0].get("is_common", False)
        self.jlpt = res[0].get("jlpt", None)
        self.reading = res[0]["japanese"][0].get("reading", None)
        for sense in res[0]["senses"]:
            if sense["parts_of_speech"] == ["Wikipedia definition"]:
                continue
            definitions = sense["english_definitions"]
            definitions = [re.sub(r"\s*\(.*?\)", "", text) for text in definitions]
            definitions = [text for text in definitions if len(text) < 30]
            if len(definitions) == 0:
                continue
            meaning = JPWordMeaning(neuances=definitions, part_of_speech=", ".join(sense["parts_of_speech"]))
            if self.llm is not None:
                structured_model = self.llm.with_structured_output(JPTranslation)
                status.update(f"Translating meaning: {meaning.neuances[0]}")
                meaning.translation = structured_model.invoke([("user", f"{self.word} : {meaning.neuances[0]}")])  # type: ignore
            self.meanings.append(meaning)

        if self.llm is not None:
            status.update("Fetching explanation from LLM")
            structured_model = self.llm.with_structured_output(JPWordExplanations)
            status.update("Generating explanation ...")
            self.explanations = structured_model.invoke(
                [
                    (
                        "user",
                        f"{self.word}({self.reading})",
                    )
                ]
            )  # type: ignore
            self._fill_synonyms_antonyms()

    def _kanji_breakdown(self) -> None:
        kanjis = self.extract_kanji(self.word)
        if not kanjis:
            return

        client = openai.OpenAI(api_key=os.getenv("openai_api_key"))
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": '# Role\r\nYou are a teacher assistant gathering materials Japanese kanjis to students with intermediate English and beginner Japanese skills.\r\n\r\n# Task\r\nWrite in a natural, conversational transcript of a teacher explaining the kanji, its meanings and readings. for each kanji (in the order it appears), compose one 3-4 short sentence paragraph that: \n1. Describes the kanji’s core meaning.\r\n2. except the original word, Presents the 1-2 vocabularies that use that kanji, and how this kanji gives meaning in this vocabulary. \n\r\n# Constrains\r\n* Explanation field is the transcription of a speech. Don\'t use bullet points, parenthesis, new lines, titles, or anything similar.\r\n* Do not include the original word in the vocabs.\r\n* In the explanation field only insert the hiragana for of Japanese vocabs. No kanjis.\r\n* Explanation starts with English phrases such as:  "The [first/second/...] kanji means ..."\n\nOutput format in json:\n{\n"word": "the given word"\n"kanjies": [\n{"kanji": "first kanji",\n"meaning": "all meanings",\n"vocabs": [{"word":"word in kanji", "hiragana": "hiragana", "meaning";"meaning"}, ...]\n}, ...\n],\n"explanation": "string"\n}\n',
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"word={self.word}, kanjis={','.join(kanjis)}"}],
                },
            ],
            text={"format": {"type": "json_object"}, "verbosity": "medium"},
            reasoning={"effort": "low", "summary": None},
            tools=[],
            store=False,
            include=["reasoning.encrypted_content", "web_search_call.action.sources"],
        )

        json_result = eval(response.output_text)
        self.kanji_explanation = json_result.get("explanation", "")
        for kanji in json_result.get("kanjies", []):
            vocabs = []
            for v in kanji.get("vocabs", []):
                vocabs.append(JPWord(word=v["word"], kanji_breakdown=False))
            kanji_data = JPKanji(kanji=kanji["kanji"])
            kanji_data.examples = vocabs
            self.kanjis.append(kanji_data)

    def _get_examples(self) -> None:
        if self.llm is None:
            return
        for c in self.explanations.collocations:
            structured_model = self.llm.with_structured_output(JPExample)
            status.update(f"Fetching example sentence for collocation: {c}")
            example = structured_model.invoke(
                [
                    (
                        "user",
                        f"Generate a natural, simple and very short Japanese example sentence using the collocation: {c} for the word {self.word} in Kanji. Sentences should be in N5 or N4 level maximum.",
                    )
                ]
            )
            self.examples.append(example)  # type: ignore

    def _fill_synonyms_antonyms(self) -> None:
        for synonym in self.explanations.synonyms or []:
            s = JPWord(word=synonym, kanji_breakdown=False)
            if s.meanings and s.reading and s.word != self.word:
                self.synonyms.append(s)
        for antonym in self.explanations.antonyms or []:
            a = JPWord(word=antonym, kanji_breakdown=False)
            if a.meanings and a.reading and a.word != self.word:
                self.antonyms.append(a)

    def save_json(self) -> None:
        os.makedirs(f"Output/{self.word}", exist_ok=True)
        with open(f"Output/{self.word}/{self.word}.json", "w", encoding="utf-8") as f:
            # f.write(self.model_dump_json(indent=4))
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=4)

    @staticmethod
    def extract_kanji(text) -> list[str]:
        return re.findall(r"[\u4E00-\u9FFF]", text)

    @staticmethod
    def query_jisho(word: str) -> dict:
        url = f"https://jisho.org/api/v1/search/words?keyword={word}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            raise Exception(f"Error fetching data from Jisho API: {response.status_code}")

    def show_in_streamlit(self, st, auth: dict | None = None) -> None:
        st.markdown(
            f"# {self.word} ({self.reading}) :orange-badge[{', '.join(self.jlpt).upper()}] :green-badge[{'Common' if self.is_common else 'Uncommon'}]"
        )
        if self.youtube_link:
            st.video(self.youtube_link)
        if self.explanations:
            st.markdown(self.explanations.motivation or "")
            st.markdown("### Meanings")
            st.markdown(self.explanations.explanation or "")
        for m in self.meanings:
            m.show_in_streamlit(st, auth)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Synonyms")
            with st.container(border=1):
                for s in self.synonyms:
                    st.write(f"**{s.word}**({s.reading}): {s.meanings[0].neuances[0]}")
        with col2:
            st.markdown("### Antonyms")
            with st.container(border=1):
                for a in self.antonyms:
                    st.write(f"**{a.word}**({a.reading}): {a.meanings[0].neuances[0]}")

        st.markdown("### Kanji")
        for k in self.kanjis:
            k.show_in_streamlit(st, original_word=self.word)

        st.markdown("### Examples")
        for ex in self.examples:
            ex.show_in_streamlit(st, auth)

    def pptx_generation(self, num_examples: int | None = 4) -> None:
        file_name = f"./Output/{self.word}/{self.word} JLPT N3 Vocabulary.pptx"
        if os.path.exists(file_name):
            status.update(f"{self.word} PowerPoint already exists, skipping...")
            return
        status.update(f"Generating PowerPoint for {self.word}...")

        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import (
            MSO_AUTO_SIZE,
            MSO_VERTICAL_ANCHOR,
            PP_PARAGRAPH_ALIGNMENT,
        )
        from pptx.util import Inches, Pt

        prs = Presentation("resources/pptx_templates/template.pptx")
        first_slide = prs.slides.add_slide(prs.slide_layouts[0])
        presentation_title = first_slide.shapes.title
        if presentation_title:
            presentation_title.text = self.word
            presentation_title.text_frame.paragraphs[0].font.size = Pt(160)
            presentation_title.text_frame.paragraphs[0].font.color.rgb = RGBColor(33, 95, 154)

        presentation_subtitle = first_slide.placeholders[1]
        presentation_subtitle.text = self.reading  # type: ignore
        presentation_subtitle.text_frame.paragraphs[0].font.size = Pt(100)  # type: ignore
        presentation_subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(192, 79, 21)  # type: ignore

        first_slide.shapes.add_movie(
            f"./output/{self.word}/audio/0_title.wav",
            left=Pt(0),
            top=Pt(-50),
            width=Pt(50),
            height=Pt(50),
            mime_type="audio/x-wav",
        )

        # Meanings slide
        explanation_slide = prs.slides.add_slide(prs.slide_layouts[6])
        shape = explanation_slide.shapes.add_textbox(Inches(5), Inches(0), Inches(40 / 3 - 5), Inches(7.5))
        shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
        shape.text_frame.word_wrap = True
        for i, meaning in enumerate(self.meanings):
            p = shape.text_frame.add_paragraph()
            p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            run = p.add_run()
            run.text = meaning.neuances[0] + "\n"
            run.font.size = Pt(115)
            run.font.name = "Berlin Sans FB Demi"
            run.font.color.rgb = RGBColor(33, 95, 154)
            if len(meaning.neuances) > 1:
                run = p.add_run()
                run.text = ", ".join(meaning.neuances[1:]) + "\n"
                run.font.size = Pt(32)
                run.font.color.rgb = RGBColor(192, 79, 21)
                run.font.name = "Berlin Sans FB"
                p.space_after = Pt(0)
                p.line_spacing = 0.9
            if meaning.translation:
                languages = [
                    ("ZH:", meaning.translation.Chinese),
                    ("FIL:", meaning.translation.Filipino),
                    ("VI:", meaning.translation.Vietnamese),
                    ("MY:", meaning.translation.Burmese),
                    ("KO:", meaning.translation.Korean),
                    ("HI:", meaning.translation.Hindi),
                    ("NE:", meaning.translation.Nepali),
                    ("FR:", meaning.translation.French),
                    ("ID:", meaning.translation.Indonesian),
                    ("FA:", meaning.translation.Persian),
                ]

                for code, translation in languages:
                    # Add bold run for the language code

                    run_code = p.add_run()
                    run_code.text = f"     {code}"
                    run_code.font.size = Pt(16)
                    run_code.font.name = "Berlin Sans FB"
                    run_code.font.color.rgb = RGBColor(127, 127, 127)

                    # Add ordinary run for the translation
                    run_translation = p.add_run()
                    run_translation.text = f"{translation}"
                    run_translation.font.size = Pt(20)
                    run_translation.font.name = "Berlin Sans FB"
                    run_translation.font.color.rgb = RGBColor(0, 0, 0)

        explanation_slide.shapes.add_movie(
            f"./output/{self.word}/audio/0_definition.wav",
            left=Pt(0),
            top=Pt(-50),
            width=Pt(50),
            height=Pt(50),
            mime_type="audio/x-wav",
        )

        # Add a slide for Kanji breakdown
        kanji_slide = prs.slides.add_slide(prs.slide_layouts[6])
        for i, kanji in enumerate(self.kanjis):
            kanji_shape = kanji_slide.shapes.add_textbox(
                Inches(0), Inches(i * 7.5 / 2), Inches(40 / 3 * 0.3), Inches(7.5 / 2)
            )
            p = kanji_shape.text_frame.add_paragraph()
            run = p.add_run()
            run.text = kanji.kanji
            run.font.size = Pt(250)
            run.font.bold = True
            run.font.name = "Yu Gothic"
            run.font.color.rgb = RGBColor(33, 95, 154)
            p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            p.space_after = Pt(0)
            p.line_spacing = 0.9

            kanji_explanation_shape = kanji_slide.shapes.add_textbox(
                Inches(40 / 3 * 0.3),
                Inches(i * 7.5 / 2),
                Inches(40 / 3 * 0.7),
                Inches(7.5 / 2),
            )
            kanji_explanation_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
            kanji_explanation_shape.text_frame.word_wrap = True
            p = kanji_explanation_shape.text_frame.paragraphs[-1]
            p.alignment = PP_PARAGRAPH_ALIGNMENT.LEFT
            run = p.add_run()
            run.text = "Meanings:"
            run.font.size = Pt(24)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(127, 127, 127)
            run = p.add_run()
            run.text = f" {', '.join(kanji.meanings)}\n"
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            run = p.add_run()
            run.text = "Readings:"
            run.font.size = Pt(24)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(127, 127, 127)
            run = p.add_run()
            run.text = f" {', '.join(kanji.onyomi + kanji.kunyomi)}\n"
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            run = p.add_run()
            for vocab in kanji.examples[:3]:
                if vocab.word == self.word:
                    continue
                run.text += f"\n{vocab.word} ({vocab.reading}): {', '.join(vocab.meanings[0].neuances)}"  # type: ignore
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(192, 79, 21)
            p.space_after = Pt(0)
            p.line_spacing = 0.9

        kanji_slide.shapes.add_movie(
            f"./output/{self.word}/audio/0_kanji.wav",
            left=Pt(0),
            top=Pt(-50),
            width=Pt(50),
            height=Pt(50),
            mime_type="audio/x-wav",
        )

        # Add a slide for examples
        for i, example in enumerate(self.examples[:num_examples]):
            collocation_slide = prs.slides.add_slide(prs.slide_layouts[6])

            top_shape = collocation_slide.shapes.add_textbox(Inches(0), Inches(0), Inches(40 / 3), Inches(3))
            top_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
            top_shape.text_frame.word_wrap = True
            top_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            p = top_shape.text_frame.add_paragraph()
            p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            run = p.add_run()
            run.text = example.kanji
            run.font.size = Pt(70)
            run.font.bold = True
            run.font.name = "Yu Gothic"
            run.font.color.rgb = RGBColor(33, 95, 154)
            run = p.add_run()
            run.text = f"\n{example.furigana}"  # type: ignore
            run.font.size = Pt(33)
            run.font.name = "Yu Gothic"
            run.font.color.rgb = RGBColor(192, 79, 21)
            p.alignment = PP_PARAGRAPH_ALIGNMENT.CENTER
            p.space_after = Pt(0)
            p.line_spacing = 0.9

            left_languages = [
                "English",
                "Chinese",
                "Filipino",
                "Vietnamese",
                "Burmese",
                "Korean",
                "Arabic",
            ]

            left_shape = collocation_slide.shapes.add_textbox(
                Inches(20 / 3 * 0.025), Inches(3), Inches(20 / 3 * 0.95), Inches(4.5)
            )
            left_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
            left_shape.text_frame.word_wrap = True
            left_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            for lang in left_languages:
                p = left_shape.text_frame.paragraphs[-1]
                p.alignment = PP_PARAGRAPH_ALIGNMENT.LEFT
                run_code = p.add_run()
                run_code.text = f"{LANGUAGES_ABBR[lang]}: "
                run_code.font.size = Pt(20)
                run_code.font.name = "Berlin Sans FB"
                run_code.font.color.rgb = RGBColor(127, 127, 127)
                run_translation = p.add_run()
                run_translation.text = f"{example.translation.__getattribute__(lang)}\n"
                run_translation.font.size = Pt(25)
                run_translation.font.name = "Berlin Sans FB"
            right_shape = collocation_slide.shapes.add_textbox(
                Inches(20 / 3 * 1.025), Inches(3), Inches(20 / 3 * 0.95), Inches(4.5)
            )
            right_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
            right_shape.text_frame.word_wrap = True
            right_shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            right_languages = [
                "Indonesian",
                "Hindi",
                "French",
                "Spanish",
                "Bengali",
                "Nepali",
                "Persian",
            ]
            for lang in right_languages:
                p = right_shape.text_frame.paragraphs[-1]
                p.alignment = PP_PARAGRAPH_ALIGNMENT.LEFT
                run_code = p.add_run()
                run_code.text = f"{LANGUAGES_ABBR[lang]}: "
                run_code.font.size = Pt(20)
                run_code.font.name = "Berlin Sans FB"
                run_code.font.color.rgb = RGBColor(127, 127, 127)
                run_translation = p.add_run()
                run_translation.text = f"{example.translation.__getattribute__(lang)}\n"  # type: ignore
                run_translation.font.size = Pt(25)
                run_translation.font.bold = False
                run_translation.font.name = "Berlin Sans FB"
            collocation_slide.shapes.add_movie(
                f"./output/{self.word}/audio/0_example_{i}.wav",
                left=Pt(0),
                top=Pt(-50),
                width=Pt(50),
                height=Pt(50),
                mime_type="audio/x-wav",
            )

        # Add a slide for synonyms and antonyms
        synonyms_slide = prs.slides.add_slide(prs.slide_layouts[6])

        synonyms_shape = synonyms_slide.shapes.add_textbox(Inches(0), Inches(0), Inches(20 / 3), Inches(7.5))
        synonyms_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
        synonyms_shape.text_frame.word_wrap = True
        p = synonyms_shape.text_frame.paragraphs[-1]
        run = p.add_run()
        run.text = "\nSYNONYMS\n\n"
        run.font.size = Pt(40)
        run.font.name = "Berlin Sans FB Demi"
        run.font.color.rgb = RGBColor(33, 95, 154)
        for i, synonym in enumerate(self.synonyms):
            run = p.add_run()
            run.text = f"{synonym.word}\n"
            run.font.size = Pt(54)
            run.font.bold = True  # type: ignore
            run.font.name = "Berlin Sans FB Demi"
            run.font.color.rgb = RGBColor(33, 95, 154)
            run = p.add_run()
            run.text = f"{synonym.reading}\n"  # type: ignore
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            run = p.add_run()
            run.text = f"{synonym.meanings[0].neuances[0]}\n\n"  # type: ignore
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            p.space_after = Pt(0)
            p.line_spacing = 0.9
        synonyms_shape.text_frame.paragraphs[0].alignment = PP_PARAGRAPH_ALIGNMENT.CENTER

        antonyms_shape = synonyms_slide.shapes.add_textbox(Inches(20 / 3), Inches(0), Inches(20 / 3), Inches(7.5))
        antonyms_shape.text_frame.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP
        antonyms_shape.text_frame.word_wrap = True
        p = antonyms_shape.text_frame.paragraphs[-1]
        run = p.add_run()
        run.text = "\nANTONYMS\n\n"
        run.font.size = Pt(40)
        run.font.name = "Berlin Sans FB Demi"
        run.font.color.rgb = RGBColor(192, 79, 21)
        for i, antonym in enumerate(self.antonyms):
            run = p.add_run()
            run.text = f"{antonym.word}\n"
            run.font.size = Pt(54)
            run.font.bold = True  # type: ignore
            run.font.name = "Berlin Sans FB Demi"
            run.font.color.rgb = RGBColor(192, 79, 21)
            run = p.add_run()
            run.text = f"{antonym.reading}\n"  # type: ignore
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            run = p.add_run()
            run.text = f"{antonym.meanings[0].neuances[0]} \n\n"  # type: ignore
            run.font.size = Pt(32)
            run.font.name = "Berlin Sans FB"
            run.font.color.rgb = RGBColor(0, 0, 0)
            p.space_after = Pt(0)
            p.line_spacing = 0.9
        antonyms_shape.text_frame.paragraphs[0].alignment = PP_PARAGRAPH_ALIGNMENT.CENTER

        synonyms_slide.shapes.add_movie(
            f"./output/{self.word}/audio/0_synonyms_antonyms.mp3",
            left=Pt(0),
            top=Pt(-50),
            width=Pt(50),
            height=Pt(50),
            mime_type="audio/x-wav",
        )

        prs.save(file_name)

    def tts(self, num_examples: int | None = 4) -> None:
        os.makedirs(f"./Output/{self.word}/audio", exist_ok=True)
        client = openai.OpenAI(api_key=os.getenv("openai_api_key"))

        # First segment
        explanation_audio_path = f"./output/{self.word}/audio/word_explanation.mp3"
        if not os.path.exists(explanation_audio_path) and self.explanations:
            status.update("Generating audio for word explanation")
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=f"{self.explanations.explanation}",
                instructions=f"English mixed with Japanese. calmly and gently. Correct pronunciation: {self.word} = {self.reading}",
                response_format="mp3",
                speed=0.95,
            )
            with open(explanation_audio_path, "wb") as audio_file:
                audio_file.write(response.content)

        motivation_audio_path = f"./output/{self.word}/audio/motivation.mp3"
        if not os.path.exists(motivation_audio_path) and self.explanations:
            status.update("Generating audio for motivation")
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=f"{self.explanations.motivation}",
                instructions=f"English mixed with Japanese. Calmly and gently. Correct pronunciation: {self.word}:{self.reading}",
                response_format="mp3",
                speed=0.95,
            )
            with open(motivation_audio_path, "wb") as audio_file:
                audio_file.write(response.content)

        title_audio = AudioSegment.from_mp3(motivation_audio_path)
        with open(f"./output/{self.word}/audio/0_title.wav", "wb") as title_file:
            title_audio.export(title_file, format="wav")

        definition_audio = AudioSegment.from_mp3(explanation_audio_path)

        with open(f"./output/{self.word}/audio/0_definition.wav", "wb") as word_file:
            definition_audio.export(word_file, format="wav")

        # Second segment
        kanji_explanation_path = f"./output/{self.word}/audio/kanji_explanation.mp3"
        if not os.path.exists(kanji_explanation_path):
            status.update("Generating audio for Kanji explanation")
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=f"{self.kanji_explanation})",
                instructions=f"English text with some japanese. Calmly and gently. correct pronunciation: {self.word}:{self.reading}",
                response_format="mp3",
                speed=0.95,
            )
            with open(kanji_explanation_path, "wb") as audio_file:
                audio_file.write(response.content)

        kanji_audio = AudioSegment.from_mp3(kanji_explanation_path)
        with open(f"./output/{self.word}/audio/0_kanji.wav", "wb") as kanji_file:
            kanji_audio.export(kanji_file, format="wav")

        for i, example in enumerate(self.examples[:num_examples]):
            example_jp_audio_path = f"./output/{self.word}/audio/example_jp_{i}.mp3"
            example_en_audio_path = f"./output/{self.word}/audio/example_en_{i}.mp3"
            if not os.path.exists(example_jp_audio_path):
                status.update(f"Generating audio for example {i}")
                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="coral",
                    input=f"{example.kanji}",
                    instructions=f"Japanese Text. Calmly and gently. correct pronunciation: {example.furigana}",
                    response_format="mp3",
                )
                with open(example_jp_audio_path, "wb") as audio_file:
                    audio_file.write(response.content)
            if not os.path.exists(example_en_audio_path):
                status.update(f"Generating audio for example {i} English")
                response = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice="coral",
                    input=f"{example.translation.English}",
                    instructions="English Text. Calmly and gently",
                    response_format="mp3",
                )
                with open(example_en_audio_path, "wb") as audio_file:
                    audio_file.write(response.content)

            example_jp_audio_segment = AudioSegment.from_mp3(example_jp_audio_path)
            example_en_audio_segment = AudioSegment.from_mp3(example_en_audio_path)

            example_audio = AudioSegment.silent(duration=1)
            example_audio += example_en_audio_segment
            example_audio += AudioSegment.silent(duration=500)
            example_audio += example_jp_audio_segment
            example_audio += AudioSegment.silent(duration=500)
            example_audio += example_jp_audio_segment

            with open(f"./output/{self.word}/audio/0_example_{i}.wav", "wb") as example_file:
                example_audio.export(example_file, format="wav")

        # Generate audio for synonyms and antonyms
        synonyms_audio_path = f"./output/{self.word}/audio/0_synonyms_antonyms.mp3"
        if not os.path.exists(synonyms_audio_path) and self.explanations:
            status.update("Generating audio for synonyms")
            response = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=f"{self.explanations.synonyms_explanation}.\n{self.explanations.antonyms_explanation}",
                instructions=f"English mixed with Japanese. Calmly and gently. correct pronunciation: {self.word}:{self.reading}",
                response_format="mp3",
                speed=0.95,
            )
            with open(synonyms_audio_path, "wb") as audio_file:
                audio_file.write(response.content)


word_list = [
    # "外出",
    # "学問",
    # "本物",
    # "外す",
    # "販売",
    # "一言",
    # "外出",
    # "激しい",
    # "議会",
    # "議長",
    # "学者",
    # "学問",
    # "品",
    # "発明",
    # "一人一人",
    # "博物館",
]


if __name__ == "__main__":
    llm_4o_openai = ChatOpenAI(model="gpt-4o", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
    llm_4o_mini_openai = ChatOpenAI(model="gpt-4o-mini", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
    llm_5_nano_openai = ChatOpenAI(model="gpt-5-nano", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
    llm_5_mini_openai = ChatOpenAI(model="gpt-5-mini", temperature=1, api_key=os.getenv("openai_api_key"))  # type: ignore
    status.start()

    for word in word_list:
        # w = JPWord(word=word, llm=llm_4o_openai)
        # w.save_json()
        w = JPWord.model_validate_json(open(f"Output/{word_list[0]}/{word_list[0]}.json", "r", encoding="utf-8").read())
        w.tts()
        w.pptx_generation()
        console.print(f"Finished processing word: {word}")

    status.stop()
