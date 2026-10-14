"""Environment-based configuration. Secrets have no defaults."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PORT: int = 8001
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    INTERNAL_API_KEY: str = ""
    MOVIES_SERVICE_URL: str = "http://localhost:8002"
    EXPRESS_API_URL: str = "http://localhost:5000"
    LLM_TIMEOUT_S: float = 30.0
    MOVIES_TIMEOUT_S: float = 10.0


settings = Settings()
