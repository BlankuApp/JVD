import os

from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from openai import OpenAI

from .logger_module import setup_logger

load_dotenv()

# Setup logger
logger = setup_logger()
logger.info("Application starting up...")

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

try:
    translator_credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    logger.info("Google Cloud credentials loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Google Cloud credentials: {e}")
    raise

_translator_client = None


def get_translator_client() -> translate.Client:
    global _translator_client
    if _translator_client is None:
        try:
            _translator_client = translate.Client(credentials=translator_credentials)
            logger.info("Google Translate client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate client: {e}")
            raise RuntimeError("Google Translate client initialization failed") from e
    return _translator_client


_openai_client = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            _openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise RuntimeError("OpenAI client initialization failed") from e
    return _openai_client
