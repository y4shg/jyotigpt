"""Environment-driven configuration for the JyotiGPT API server.

Every setting maps to an environment variable; names that configure external
services keep the same names as the previous implementation so existing
deployments keep working (see REWRITE.md -> Env vars).
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "./data")).resolve()


def _load_or_create_secret(data_dir: Path, env_value: str | None) -> str:
    """Return the configured secret, or a persisted randomly-generated one."""
    if env_value and env_value.strip():
        return env_value.strip()
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / ".secret"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


class Settings(BaseSettings):
    """Application settings, sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- core ---
    app_name: str = "JyotiGPT"
    app_env: str = "development"  # development | production
    data_dir: Path = Field(default_factory=_default_data_dir)
    database_url: str = ""  # empty -> sqlite under DATA_DIR
    webui_url: str = "http://localhost:3001"  # public URL for share links
    frontend_origins: str = "http://localhost:3001,http://localhost:3000,http://localhost:8080"
    trust_x_forwarded_for: bool = False

    # --- auth / sessions ---
    jwt_secret_key: str = Field(default="", description="JYOTIGPT_JWT_SECRET_KEY alias")
    jwt_expires_in: str = "30d"  # timedelta string, e.g. "30d", "12h", "7d"
    enable_signup: bool = True
    default_user_role: str = "pending"  # pending | user | admin
    enable_api_keys: bool = True
    jwt_algorithm: str = "HS256"

    # first-boot admin bootstrap (own design)
    admin_email: str = "admin@jyoti.local"
    admin_password: str = "admin"

    # --- LDAP (optional, off by default) ---
    enable_ldap: bool = False
    ldap_server_host: str = "localhost"
    ldap_server_port: int = 389
    ldap_app_dn: str = ""
    ldap_app_password: str = ""
    ldap_search_base: str = ""
    ldap_search_filter: str = "(mail={{mail}})"
    ldap_attribute_for_mail: str = "mail"
    ldap_attribute_for_username: str = "cn"
    ldap_use_tls: bool = False
    ldap_ca_cert_file: str = ""

    # --- trusted-header reverse-proxy auth (off by default) ---
    auth_trusted_email_header: str = ""
    auth_trusted_name_header: str = ""

    # --- model providers ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_num_predict: int = -1
    ollama_keep_alive: str = "5m"
    openai_api_key: str = ""
    openai_api_base_url: str = "https://api.openai.com/v1"
    openai_api_models: str = ""  # comma list to expose
    openai_default_model: str = "gpt-4o-mini"
    openai_request_timeout: float = 60.0

    # --- voice ---
    audio_stt_engine: str = ""  # "" | openai | browser
    audio_stt_openai_api_key: str = ""
    audio_stt_openai_base_url: str = ""
    audio_stt_openai_model: str = "whisper-1"
    audio_tts_engine: str = ""  # "" | openai | browser
    audio_tts_openai_api_key: str = ""
    audio_tts_openai_base_url: str = ""
    audio_tts_openai_model: str = "gpt-4o-mini-tts"
    audio_tts_openai_voice: str = "alloy"

    # --- web search ---
    enable_web_search: bool = False
    searxng_query_url: str = ""
    searxng_secret: str = ""
    web_search_result_count: int = 10

    # --- image generation ---
    enable_image_generation: bool = False
    enable_image_prompt_generation: bool = False
    image_prompt_generation_prompt_template: str = (
        "Generate a prompt to generate an image for a given text. Only reply with "
        "the prompt, no surrounding text or quotation marks. The prompt must be "
        "in English and must be a single sentence. Text: {{TEXT}}"
    )
    image_generation_engine: str = "openai"  # openai | automatic1111 | comfyui
    image_generation_openai_api_key: str = ""
    image_generation_openai_base_url: str = ""
    image_generation_openai_model: str = "dall-e-3"
    automatic1111_base_url: str = ""
    comfyui_base_url: str = ""
    comfyui_workflow: str = ""
    comfyui_api_key: str = ""
    user_permissions_features_image_generation: bool = True

    # --- uploads / documents ---
    max_upload_size_mb: int = 512
    content_extraction_max_mb: int = 10  # files larger than this are stored, not parsed

    # --- retrieval (RAG) ---
    rag_embedding_model: str = ""  # empty -> try "nomic-embed-text" on Ollama
    rag_chunk_size: int = 1000  # characters per chunk
    rag_chunk_overlap: int = 100
    rag_top_k: int = 4  # default number of chunks returned by search

    def model_post_init(self, __context) -> None:
        """Ensure the data directory exists before the engine connects."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # --- misc toggles ---
    enable_markdown: bool = True
    enable_rag: bool = True
    enable_rooms: bool = True

    # --- compat: old names -> new names (back-compat reading) ---
    @property
    def secret_key(self) -> str:
        """Resolved signing secret (env 'JYOTIGPT_JWT_SECRET_KEY' or 'JYOTI_SECRET_KEY')."""
        value = os.environ.get("JYOTIGPT_JWT_SECRET_KEY") or os.environ.get("JYOTI_SECRET_KEY")
        return _load_or_create_secret(self.data_dir, value)

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.data_dir / 'jyoti.db'}"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
