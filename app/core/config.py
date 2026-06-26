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
    max_document_upload_bytes: int = 5 * 1024 * 1024
    request_timeout_seconds: int = 30
    tool_timeout_seconds: int = 10
    llm_timeout_seconds: int = 30
    max_tool_calls_per_run: int = 10
    max_retrieval_results: int = 10
    max_eval_cases: int = 25
    agno_enabled: bool = True
    agno_model: str = "mock-agno-agent"
    agno_allow_real_provider: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
