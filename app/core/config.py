from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "agentic_rag_workbench"
    )
    app_env: str = "development"
    log_level: str = "INFO"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "business_documents"
    embedding_provider: str = "mock"
    llm_provider: str = "mock"
    llm_model: str = "mock-trace-generator"
    llm_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    deepseek_api_key: str | None = None
    chunk_size: int = 800
    chunk_overlap: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
