"""Environment configuration for the backend."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "")
        # LLM: Google Gemini via its OpenAI-compatible endpoint.
        # MISTRAL_* vars are read as a convenience fallback so an existing
        # deployment keeps working after the provider switch.
        self.llm_api_key = os.getenv("LLM_API_KEY", os.getenv("MISTRAL_API_KEY", ""))
        self.llm_base_url = os.getenv(
            "LLM_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai",
        ).rstrip("/")
        self.llm_model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        # Minimum spacing between consecutive LLM calls. Gemini's free tier
        # allows roughly 10 requests/minute for flash models; the default is
        # deliberately conservative. Check AI Studio and tune.
        self.min_interval_ms = int(
            os.getenv("LLM_MIN_INTERVAL_MS", os.getenv("MISTRAL_MIN_INTERVAL_MS", "6000"))
        )
        self.session_idle_minutes = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
        self.export_dir = os.getenv("EXPORT_DIR", "static/exports")
        self.frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")


settings = Settings()
