# JVD Codebase Refactoring Todo List

## High Priority Refactorings

### 1. Database Client Duplication
- [ ] **Consolidate Supabase client initialization**
  - Currently initialized in 5+ places: `main.py`, `src/utils.py`, `src/web/user.py`, `src/db/db_word.py`
  - Create a single `src/db/client.py` with `get_supabase_client()` function
  - Remove all duplicate `load_dotenv()` and `create_client()` calls
  - Use dependency injection or global singleton pattern

### 2. Error Handling & Logging
- [ ] **Replace print() statements with proper logging**
  - Found 18+ `print()` statements for errors across the codebase
  - Replace all `print(f"Error...")` with `logger.error()` calls
  - Files to update: `src/db/db_word.py`, `src/utils.py`, `src/upload_video.py`, `src/word/BatchWord.py`
  - Ensure consistent error message formatting

- [ ] **Standardize exception handling in database operations**
  - All functions return `tuple[bool, str]` but catch generic `Exception`
  - Create custom exception types: `DatabaseError`, `AuthenticationError`, `ValidationError`
  - Add specific exception handlers for Supabase errors
  - Log full stack traces for debugging

### 3. Authentication Architecture
- [ ] **Centralize auth object structure and validation**
  - Auth dict is manually constructed in 4+ places with inconsistent fields
  - Create `src/auth/auth_model.py` with `AuthUser` dataclass/Pydantic model
  - Define required fields: `id`, `email`, `username`, `jlpt_level`, `preferred_languages`, `access_token`, `refresh_token`
  - Add validation for missing fields
  
- [ ] **Create unified authentication service**
  - Move `authenticate()` from `src/utils.py` to `src/auth/service.py`
  - Consolidate login, signup, token refresh, and session management
  - Remove auth logic duplication in `src/web/user.py`
  - Handle token expiration and automatic refresh

### 4. Session State Management
- [ ] **Refactor session state handling**
  - Create `src/web/session_manager.py` for centralized session state
  - Define TypedDict or Pydantic models for all session state keys
  - Current manual dict access is error-prone: `st.session_state.get("auth", None)`
  - Add session state initialization and cleanup utilities
  - Document all session state keys and their types

### 5. Configuration Management
- [ ] **Create centralized configuration system**
  - Move all constants from scattered locations to `src/config.py`
  - Use Pydantic Settings for environment variables
  - Current issues: `LANGUAGES_ABBR` defined in `src/__init__.py`, magic strings everywhere
  - Add validation for required environment variables at startup
  - Create separate configs for dev/prod environments

### 6. API Client Initialization
- [ ] **Refactor global client pattern**
  - Current pattern in `src/__init__.py`: `if "_translator_client" not in globals()`
  - Use proper singleton pattern or dependency injection
  - Both `get_translator_client()` and `get_openai_client()` have complex error handling
  - Consider lazy loading with `functools.lru_cache` decorator
  - Add health check methods for clients

### 7. Database Query Patterns
- [ ] **Create repository pattern for database operations**
  - Current: All queries in `src/db/db_word.py` as standalone functions
  - Create `UserCardRepository` and `WordRepository` classes
  - Benefits: Better testability, consistent error handling, connection pooling
  - Add query builders for complex queries (get_due_card, etc.)
  - Implement proper transaction support

### 8. Card State Hydration
- [ ] **Simplify card hydration logic**
  - `ReviewStateManager._hydrate_card()` has complex datetime parsing
  - `_parse_datetime()` duplicates datetime logic
  - Create `CardSerializer` class for Card <-> DB conversion
  - Move FSRS-specific logic to pyfsrs module
  - Add proper error messages for invalid card data

## Medium Priority Refactorings

### 9. Review Workflow State Machine
- [ ] **Formalize state machine implementation**
  - Current: Manual state strings in `ReviewStateManager.STATES` dict
  - Use `enum.Enum` for review states
  - Add state transition validation (prevent invalid transitions)
  - Create state diagram documentation
  - Add logging for state transitions

### 10. Word Data Schema Versioning
- [ ] **Consolidate word schema migrations**
  - Three versions: 0.1.1, 0.2.0, 0.3.0 in `src/word/migrate.py`
  - Complex migration logic with duplicate code
  - Create schema version registry
  - Add automated migration tests
  - Consider using Pydantic discriminated unions for version handling

### 11. Type Hints & Type Safety
- [ ] **Add comprehensive type hints**
  - Many functions missing return type hints
  - Use of `dict` instead of `TypedDict` for structured data
  - Add `from __future__ import annotations` to all modules
  - Run mypy and fix type errors
  - Use Protocol for interface definitions

### 12. UI Component Reusability
- [ ] **Extract common Streamlit UI patterns**
  - Badge rendering: `:orange-badge[N{level}]` duplicated in multiple files
  - Create `src/web/components/` directory
  - Extract: `render_badge()`, `render_word_card()`, `render_language_filter()`
  - Standardize toast notification patterns
  - Create reusable form components

### 13. AI Question Generation
- [ ] **Standardize LLM usage patterns**
  - Found in: `src/pyfsrs/card.py`, `src/web/kanji_reading.py`
  - Two LLM clients defined but inconsistently used: `llm_4o_mini_openai`, `llm_5_mini_openai`
  - Create `src/ai/llm_service.py` with unified interface
  - Add retry logic and rate limiting
  - Implement prompt templates system

### 14. File Organization
- [ ] **Restructure web pages directory**
  - Current: All pages in `src/web/` as flat structure
  - Create subdirectories: `src/web/pages/`, `src/web/components/`, `src/web/layouts/`
  - Move state management to `src/web/state/`
  - Move UI components to dedicated files

### 15. Audio Processing
- [ ] **Extract audio functionality to service**
  - Audio processing in `src/web/review_processing.py`
  - Create `src/services/audio_service.py`
  - Add audio format validation
  - Support multiple audio codecs
  - Add audio quality settings

## Low Priority Refactorings

### 16. Testing Infrastructure
- [ ] **Add comprehensive test suite**
  - No unit tests found in codebase
  - Create `tests/` directory structure
  - Add pytest configuration
  - Write tests for critical paths: auth, FSRS, database ops
  - Add integration tests for Streamlit pages

### 17. Data Validation
- [ ] **Add Pydantic validation for all models**
  - Currently: Manual validation or no validation
  - Files to update: word models, card models, user models
  - Validate JLPT levels (1-5), language codes, dates
  - Add custom validators for Japanese text

### 18. Resource Loading
- [ ] **Optimize word resource loading**
  - `@st.cache_data` used but may not be optimal
  - Word JSON files loaded repeatedly
  - Consider database-first approach vs file-based
  - Add resource preloading on startup
  - Implement lazy loading for large datasets

### 19. Video Upload Service
- [ ] **Refactor YouTube upload functionality**
  - `src/upload_video.py` has hardcoded values
  - Extract YouTube API client to service class
  - Add video upload queue system
  - Implement retry logic for failed uploads
  - Add thumbnail generation automation

### 20. Environment Variable Handling
- [ ] **Improve secret management**
  - Encrypted credentials in `gdata` file with Fernet
  - Complex temp file creation in `get_translator_client()`
  - Consider using proper secret management (AWS Secrets Manager, Azure Key Vault)
  - Add credential rotation support
  - Validate credentials at startup

### 21. Logging Configuration
- [ ] **Enhance logging system**
  - Current: `src/logger_module.py` with basic file logging
  - Add structured logging (JSON format)
  - Implement log rotation by size (not just date)
  - Add different log levels per module
  - Consider centralized logging service integration

### 22. PowerPoint Generation
- [ ] **Refactor PPTX generation**
  - Duplicated logic in `JPWord.pptx_generation()` and `JPWordInfo.pptx_generation()`
  - Extract to `src/services/pptx_service.py`
  - Create template-based approach
  - Add error handling for missing resources
  - Support multiple template styles

### 23. Database Migration System
- [ ] **Implement proper database migrations**
  - Current: Manual SQL or scripts
  - Add Alembic for database version control
  - Track schema changes
  - Add rollback capabilities
  - Document migration procedures

### 24. Code Documentation
- [ ] **Add comprehensive docstrings**
  - Many functions missing docstrings
  - Use Google or NumPy docstring format consistently
  - Document complex algorithms (FSRS)
  - Add usage examples in docstrings
  - Generate API documentation with Sphinx

### 25. Performance Optimization
- [ ] **Profile and optimize bottlenecks**
  - Review database query performance
  - Optimize word loading (consider pagination)
  - Cache expensive AI operations
  - Add performance monitoring
  - Optimize Streamlit page load times

## Code Quality Improvements

### 26. Code Formatting
- [ ] **Enforce consistent code style**
  - Add black configuration
  - Add isort for import sorting
  - Add flake8 or ruff for linting
  - Set up pre-commit hooks
  - Configure line length and other style rules

### 27. Dependency Management
- [ ] **Update requirements.txt**
  - Pin all dependency versions
  - Separate dev dependencies
  - Document why each dependency is needed
  - Check for security vulnerabilities
  - Remove unused dependencies

### 28. Magic Numbers & Strings
- [ ] **Replace magic values with constants**
  - Font sizes, dimensions, timeouts scattered in code
  - Create `src/constants.py` for UI constants
  - Use enums for categorical values
  - Document meaning of each constant

---

## Implementation Priority Order

1. **Phase 1 (Critical)**: Items 1-8 - Core architecture improvements
2. **Phase 2 (Important)**: Items 9-15 - Feature-specific refactorings
3. **Phase 3 (Nice to have)**: Items 16-25 - Quality and scalability
4. **Phase 4 (Polish)**: Items 26-28 - Code quality and maintenance

## Notes

- Each checkbox should be checked off as work is completed
- Create separate Git branches for each major refactoring
- Add tests before and after refactoring
- Update CLAUDE.md documentation as architecture changes
- Consider backward compatibility for database changes
