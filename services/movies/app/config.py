"""Environment-based configuration for the movies service.

All runtime secrets and connection details come from environment variables.
See ../.env.example for placeholder values. No defaults contain secrets.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "cinemind"
    MONGODB_COLLECTION: str = "movies"
    PORT: int = 8002
    INTERNAL_API_KEY: str = ""


settings = Settings()
