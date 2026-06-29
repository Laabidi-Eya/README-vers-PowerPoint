import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

groq_client = None

if _OPENROUTER_API_KEY:
    try:
        groq_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=_OPENROUTER_API_KEY,
        )
        logger.info("LLM client: OpenRouter")
    except Exception as e:
        logger.error("Failed to initialize OpenRouter client: %s", e)
elif USE_LLM:
    logger.error("USE_LLM is true but OPENROUTER_API_KEY is not set.")


def luminance(r: int, g: int, b: int) -> float:
    return 0.299 * r + 0.587 * g + 0.114 * b
