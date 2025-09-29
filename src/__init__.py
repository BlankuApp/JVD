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
        inp = None
        try:
            try:
                # Replace literal \n with actual newlines in the private key
                private_key = os.getenv("GOOGLE_CLOUD_PRIVATE_KEY")
                if private_key:
                    private_key = private_key.replace("\\n", "\n")

                inp = {
                    "type": "service_account",
                    "project_id": "flawless-shard-472208-f2",
                    "private_key_id": os.getenv("GOOGLE_CLOUD_PRIVATE_KEY_ID"),
                    "private_key": private_key,
                    "client_email": os.getenv("GOOGLE_CLOUD_CLIENT_EMAIL"),
                    "client_id": os.getenv("GOOGLE_CLOUD_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/translation-service%40flawless-shard-472208-f2.iam.gserviceaccount.com",
                    "universe_domain": "googleapis.com",
                }

                translator_credentials = service_account.Credentials.from_service_account_info(info=inp)
                logger.info("Google Cloud credentials loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Google Cloud credentials: {e}")
                raise RuntimeError(f"Google Cloud credentials loading failed \n\n{inp}") from e
            _translator_client = translate.Client(credentials=translator_credentials)
            logger.info("Google Translate client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate client: {e}")
            raise RuntimeError(f"Google Translate client initialization failed {e} \n\n{inp}") from e
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


_ = get_translator_client()
