# Copilot Instructions for JVD (Japanese Video Dictionary)

## Project Overview
JVD is a Streamlit-based Japanese language learning application that combines spaced repetition (FSRS algorithm), AI-powered content generation, and YouTube video integration for JLPT vocabulary study.

## Key Architecture Components

### Core Structure
- **Main Entry**: `main.py` - Streamlit multi-page app with Supabase authentication 
- **Web Pages**: `src/web/` - Individual Streamlit pages (main_page, v, review, fill_in_the_blank, user)
- **Data Layer**: `src/db/db_word.py` - Supabase database operations for user cards and vocabulary
- **FSRS System**: `src/pyfsrs/` - Custom implementation of spaced repetition algorithm
- **Word Models**: `src/word/` - JPWord and JPWord2 classes for vocabulary data with AI explanations

### Authentication Pattern
Uses Streamlit session state + cookie-based persistence:
```python
auth = st.session_state.get("auth", None)
# Always check auth before accessing user-specific features
if not auth:
    st.warning("You need to be logged in...")
    st.stop()
```
Auth object contains: `id`, `email`, `username`, `jlpt_level`, `preferred_languages`, `access_token`

### FSRS Integration
- **JPWordCard** extends base Card class with AI question generation methods
- **Scheduler** handles spaced repetition timing with 95% retention rate target
- **Rating enum**: Again, Hard, Good, Easy - affects next review scheduling
- Cards have states: Learning, Review, Relearning with specific step progressions

### Content Generation
- **OpenAI Integration**: Uses `gpt-4o-mini` for question generation and `gpt-4o` for review
- **Google Translate**: Encrypted credentials stored in `gdata` file, decrypted with Fernet
- **Multi-language Support**: 14 languages with user preference filtering

### Data Storage Patterns
- **Word Resources**: JSON files in `resources/words/` with versioned schemas (0.1.1 vs 0.2.0)
- **User Cards**: Supabase table tracking individual progress with FSRS parameters
- **Session State**: Extensive use for review workflows and UI state management

## Development Workflows

### Running the Application
```bash
# Use the configured task
python -m streamlit run main.py
# Or via VS Code task: "streamlit"
```

### Adding New Vocabulary
```bash
# Run the upload script to sync JSON files to database
python src/db/db_word.py
```

### Key Environment Variables
- `OPENAI_API_KEY` - For AI content generation
- `FKEY` - Fernet encryption key for Google credentials  
- `supabaseUrl`, `supabaseKey` - Database connection

## Component Communication

### Review Workflow
1. `get_due_card()` fetches next card from database
2. `JPWordCard.generate_reverse_translation_question()` creates AI question
3. User answers → `JPWordCard.review_reverse_translation_question()` AI grading
4. `Scheduler.review_card()` calculates next due date
5. `update_user_word_card()` persists FSRS state to database

### Word Display Pattern
Both JPWord classes implement `show_in_streamlit(st, auth)` method that:
- Filters content by user's preferred languages
- Shows JLPT level badges and YouTube videos
- Renders ruby text (furigana) with `create_html_with_ruby()`
- Provides add/remove word functionality

### Page Navigation
Uses `st.query_params` for word details and `st.switch_page()` for navigation. Auth state persists across pages via session state.

## Project-Specific Conventions

### Error Handling
- Database operations return `(bool, str)` tuples for success/message
- Client initialization uses global variables with lazy loading pattern
- Extensive try-catch with user-friendly toast notifications

### UI Patterns
- Consistent use of `st.toast()` for user feedback with icons
- `st.container(border=True)` for grouped content
- Badge styling: `:orange-badge[N{level}]`, `:gray-badge[{lang}]`
- Loading states with `st.spinner("message...", show_time=True)`

### File Organization
- Encrypted credentials for production APIs
- JSON word data with `in_db` flags to track upload status
- Logging to `logs/` directory with date-based rotation

## Critical Dependencies
- **Streamlit**: Multi-page app framework with session management
- **Supabase**: Authentication and PostgreSQL database
- **py-fsrs**: Custom spaced repetition implementation 
- **LangChain + OpenAI**: AI content generation and review
- **Google Cloud Translate**: Multi-language support