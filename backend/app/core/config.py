from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BUSINESS_LINES: tuple[str, ...] = ("autos", "hogar", "vida")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_parse_none_str="")

    database_url: str = "postgresql://brisamar_app:brisamar_app@localhost:5432/brisamar"
    database_admin_url: str = "postgresql://postgres:postgres@localhost:5432/brisamar"
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False

    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 300

    llm_provider: Literal["fake", "litellm"] = "fake"
    llm_model: str = "gemini/gemini-2.5-flash"
    llm_timeout_seconds: float = 30.0
    llm_max_attempts: int = 4
    embedding_provider: Literal["fake", "litellm"] = "fake"
    embedding_model: str = "gemini/gemini-embedding-001"
    embedding_dim: int = 768

    chunk_max_chars: int = 700
    chunk_overlap_chars: int = 150
    retrieval_candidates: int = 20
    retrieval_top_k: int = 5
    rrf_k: int = 60
    min_vector_similarity: float | None = Field(
        default=None,
        description="Evidence gate. When unset, the embedding provider default is used.",
    )

    cors_origins: list[str] = ["http://localhost:5173"]

    otel_exporter: Literal["console", "otlp", "none"] = "console"
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "brisamar-rag"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
