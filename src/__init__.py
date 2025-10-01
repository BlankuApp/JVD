import os
import tempfile
import json

from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account
from openai import OpenAI
from cryptography.fernet import Fernet

from .logger_module import setup_logger

load_dotenv()

# Setup logger
logger = setup_logger(level="INFO")

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

if "_translator_client" not in globals():
    _translator_client = None


def get_translator_client() -> translate.Client:
    global _translator_client
    if _translator_client is None:
        try:
            try:
                fernet = Fernet(os.getenv("FKEY"))
                with open("gdata", "rb") as file:
                    encrypted_data = file.read()
                    decrypted_data = fernet.decrypt(encrypted_data)
                    inp = json.loads(decrypted_data.decode())
                # Validate the service account info
                service_account.Credentials.from_service_account_info(info=inp)
                logger.info("Google Cloud credentials loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Google Cloud credentials: {e}")
                raise RuntimeError("Google Cloud credentials loading failed") from e

            # Initialize the client with credentials using temporary file method
            temp_file_path = None
            try:
                # Create a temporary file with the service account info
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
                    json.dump(inp, temp_file)
                    temp_file_path = temp_file.name

                # Set the environment variable to point to the temp file
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
                _translator_client = translate.Client()

                # Clean up the temporary file
                os.unlink(temp_file_path)
                logger.info("Google Translate client initialized")
            except Exception as e:
                # Clean up temp file if it exists
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise e
        except Exception as e:
            logger.error(f"Failed to initialize Google Translate client: {e}")
            raise RuntimeError(f"Google Translate client initialization failed {e}") from e
    return _translator_client


if "_openai_client" not in globals():
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
