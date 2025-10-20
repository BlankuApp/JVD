# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JVD (Japanese Video Dictionary) is a Streamlit-based Japanese language learning application that combines spaced repetition (FSRS algorithm), AI-powered content generation, and YouTube video integration for JLPT vocabulary study.

## Running the Application
The application is developed on windows with power shell.
```bash
# Start the Streamlit web application (uses .venv virtual environment)
python -m streamlit run main.py
```

## Development Commands

```bash
# Upload vocabulary JSON files from resources/words/ to Supabase database
python src/db/db_word.py

# Generate new vocabulary words with AI explanations
python -m src.word.JPWord

# Upload YouTube videos for vocabulary
python -m src.upload_video

# Run any Python file directly
python <file_path>
```

## Project Structure

```
JVD/
├── main.py                     # Streamlit app entry point with multi-page navigation
├── src/
│   ├── web/                    # Streamlit pages
│   │   ├── main_page.py        # Home page
│   │   ├── v.py                # JLPT vocabularies browser
│   │   ├── review.py           # Spaced repetition review workflow
│   │   ├── fill_in_the_blank.py
│   │   ├── kanji_reading.py
│   │   └── user.py             # Login/profile page
│   ├── word/                   # Vocabulary models and generation
│   │   ├── JPWord.py           # Japanese word class with AI generation
│   │   ├── BatchWord.py
│   │   └── migrate.py
│   ├── db/
│   │   └── db_word.py          # Supabase database operations
│   ├── pyfsrs/                 # Custom FSRS spaced repetition implementation
│   │   ├── card.py             # JPWordCard with AI question generation
│   │   ├── scheduler.py        # Review scheduling (95% retention target)
│   │   ├── review_log.py       # Rating enum (Again, Hard, Good, Easy)
│   │   └── optimizer.py
│   ├── utils.py                # Authentication and UI helpers
│   └── logger_module.py
├── resources/words/            # JSON files for vocabulary data (versioned schemas)
└── logs/                       # Application logs
```

## Architecture Overview

### Authentication System

Uses Streamlit session state with cookie-based persistence via `streamlit-cookies-controller`:

```python
auth = st.session_state.get("auth", None)
if not auth:
    st.warning("You need to be logged in...")
    st.stop()
```

Auth object contains: `id`, `email`, `username`, `jlpt_level`, `preferred_languages`, `access_token`

All pages requiring authentication should check for `auth` in session state before proceeding.

### FSRS Spaced Repetition System

- **JPWordCard** (in `src/pyfsrs/card.py`) extends base Card class with AI question generation methods
- **Scheduler** calculates next review dates targeting 95% retention rate
- **Card States**: Learning, Review, Relearning with specific step progressions
- **Rating System**: Again, Hard, Good, Easy - affects scheduling intervals
- User progress tracked in Supabase `user_card` table with FSRS parameters: `stability`, `difficulty`, `due`, `step`, `state`

### Review Workflow

1. `get_due_card(auth)` fetches next card from database based on due date
2. `JPWordCard.generate_reverse_translation_question()` creates AI-powered question using OpenAI
3. User submits answer (text or voice)
4. `JPWordCard.review_reverse_translation_question()` grades answer with AI
5. `Scheduler.review_card()` calculates next due date based on rating
6. `update_user_word_card()` persists updated FSRS state to database

### AI Content Generation

- **OpenAI Models**: Uses `gpt-4o-mini` for question generation and `gpt-4o` for review/grading
- **Google Cloud Translate**: Multi-language support (14 languages) - credentials encrypted with Fernet in `gdata` file
- **Content Types**: Word explanations, collocations, example sentences, kanji breakdowns, synonyms/antonyms
- All AI-generated content stored in JSON files under `resources/words/`

### Data Layer

**Supabase Tables:**
- `words`: Core vocabulary with JLPT levels
- `user_card`: Individual user progress tracking with FSRS parameters
  - Fields: `user_id`, `type`, `key` (word), `state`, `step`, `stability`, `difficulty`, `due`, `last_review`
  - Type is always "JPWord" for vocabulary cards

**Database Operation Pattern:**
- All database functions return `(bool, str)` tuples for success/error messages
- Client initialized lazily with global variables
- Extensive try-catch with user-friendly toast notifications

**Word Resource Files:**
- JSON files in `resources/words/` with versioned schemas (0.1.1, 0.2.0, 0.3.0)
- Contains: word, jlpt_level, youtube_link, kanji_data, meanings_translations, collocations, example_sentences, jisho_data
- `in_db` flag tracks upload status to Supabase

### Vocabulary Word Display

Both JPWord classes implement `show_in_streamlit(st, auth)` method:
- Filters content by user's preferred languages from auth object
- Displays JLPT level with `:orange-badge[N{level}]` styling
- Embeds YouTube videos for visual learning
- Renders ruby text (furigana) using `create_html_with_ruby()` helper
- Provides add/remove word functionality for user's card collection

### Page Navigation

- Uses `st.query_params` for passing word details between pages
- `st.switch_page()` for programmatic navigation
- Auth state persists across pages via session state
- Due review count badge updates dynamically in navigation (shown in main.py:30)

## Environment Variables

Required in `.env` file:

```
OPENAI_API_KEY         # For AI content generation
FKEY                   # Fernet encryption key for Google credentials
supabaseUrl            # Database connection URL
supabaseKey            # Database API key
```

## UI Patterns and Conventions

**Streamlit Components:**
- `st.toast()` for user feedback with icons (e.g., `:material/check: Success!`)
- `st.container(border=True)` for grouped content sections
- `st.spinner("message...", show_time=True)` for loading states
- Badge styling: `:orange-badge[N{level}]`, `:gray-badge[{lang}]`

**Ruby Text (Furigana):**
- Use `create_html_with_ruby()` helper from `src/utils.py`
- Format: `word(reading)` becomes HTML with ruby annotations

**Multi-language Filtering:**
- Always filter translations by `auth["preferred_languages"]`
- Language order: EN, ID, ES, VI, FR, NE, BN, ZH, KO, TL, MY, HI, AR, FA

## Important Implementation Details

**External APIs:**
- Jisho API: `https://jisho.org/api/v1/search/words?keyword={word}` for word definitions
- Kanji API: `https://kanjiapi.dev/v1/kanji/{kanji}` for kanji information
- Both return JSON; handle missing data gracefully

**Audio Processing:**
- Uses `pydub` for audio segment manipulation
- OpenAI Whisper for speech-to-text in review workflow

**Logging:**
- Custom logger in `src/logger_module.py`
- Logs to `logs/` directory with date-based rotation
- Use emoji prefixes for log categorization

**Word Schema Versions:**
- v0.1.1: Original schema
- v0.2.0: Added `meanings_translations` field
- v0.3.0: Current version with enhanced AI explanations
- Schemas are not backward compatible; migration scripts in `src/word/migrate.py`

## Virtual Environment

Project uses `.venv` virtual environment. VS Code tasks are configured to use `.venv/Scripts/python.exe` on Windows.
