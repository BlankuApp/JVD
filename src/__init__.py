import os
import json

from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from openai import OpenAI

from .logger_module import setup_logger

load_dotenv()

# Setup logger
logger = setup_logger(level="INFO")
logger.info("Application starting up...")

LANGUAGES_ABBR = {
    "English": "EN",
    "Indonesian": "ID",
    "Spanish": "ES",
    "Vietnamese": "VI",
    "French": "FR",
    "Nepali": "NE",
    "Bengali": "BN",
    "Chinese": "ZH",
    "Korean": "KO",
    "Filipino": "TL",
    "Burmese": "MY",
    "Hindi": "HI",
    "Arabic": "AR",
    "Persian": "FA",
}

_translator_client = None


def get_translator_client() -> translate.Client:
    global _translator_client
    if _translator_client is None:
        try:
            try:
                translator_credentials = service_account.Credentials.from_service_account_info(
                    json.loads(os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON", "{}"))
                )
                logger.info("Google Cloud credentials loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Google Cloud credentials: {e}")
                raise RuntimeError("Google Cloud credentials loading failed") from e
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
