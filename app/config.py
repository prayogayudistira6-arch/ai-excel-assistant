from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    app_env: str = "dev"
    log_level: str = "INFO"
    input_dir: str = "data/input"
    output_dir: str = "data/output"
    default_output_file: str = "data/output/assistant_output.xlsx"
    llm_mode: str = "mock"
    ai_provider: str = "rule_based"
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-5.5"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    country_api_mode: str = "mock"
    country_api_base_url: str = "https://api.worldbank.org/v2"
    request_timeout_seconds: int = 10
    streamlit_max_upload_mb: int = 50


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        input_dir=os.getenv("INPUT_DIR", "data/input"),
        output_dir=os.getenv("OUTPUT_DIR", "data/output"),
        default_output_file=os.getenv("DEFAULT_OUTPUT_FILE", "data/output/assistant_output.xlsx"),
        llm_mode=os.getenv("LLM_MODE", "mock"),
        ai_provider=os.getenv("AI_PROVIDER", os.getenv("LLM_PROVIDER", "rule_based")),
        ai_api_key=os.getenv("AI_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        ai_base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
        ai_model=os.getenv("AI_MODEL", os.getenv("OPENAI_MODEL", "gpt-5.5")),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
        country_api_mode=os.getenv("COUNTRY_API_MODE", "mock"),
        country_api_base_url=os.getenv("COUNTRY_API_BASE_URL", "https://api.worldbank.org/v2"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        streamlit_max_upload_mb=int(os.getenv("STREAMLIT_MAX_UPLOAD_MB", "50")),
    )
