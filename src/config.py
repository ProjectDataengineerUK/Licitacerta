from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic (Claude Sonnet for compliance, Opus opt-in)
    anthropic_api_key: str = ""
    model_sonnet: str = "claude-sonnet-4-6"
    model_opus: str = "claude-opus-4-7"
    model_haiku: str = "claude-haiku-4-5-20251001"

    # GCP
    gcp_project_id: str = ""
    gcp_region: str = "southamerica-east1"
    vertex_ai_location: str = "us-central1"  # Gemini models are published in us-central1
    document_ai_location: str = "us"
    document_ai_processor_id: str = ""
    gcs_bucket_docs: str = ""
    alloydb_instance_uri: str = "postgresql://localhost/licitacerta"
    alloydb_db: str = "licitacerta"
    tasks_queue_hitl: str = "hitl-approvals"

    # Gemini model IDs (Vertex AI)
    gemini_flash: str = "gemini-1.5-flash-002"
    gemini_pro: str = "gemini-1.5-pro-002"
    gemini_generate: str = "gemini-1.5-pro-002"

    # Other
    cgu_api_key: str = ""
    database_url: str = "postgresql://localhost/licitacerta"
    redis_url: str = "redis://localhost:6379/0"

    max_cost_per_analysis_brl: float = 0.90


settings = Settings()
