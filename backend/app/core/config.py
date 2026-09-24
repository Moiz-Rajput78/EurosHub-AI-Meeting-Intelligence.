from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = "Meeting Intelligence"
    app_env: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = "sqlite:///./meetings.db"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 500

    ollama_mode: str = "cloud"
    ollama_base_url: str = "https://ollama.com"
    ollama_api_key: str = ""
    ollama_model: str = "gemma4:cloud"
    analysis_chunk_chars: int = 12000
    analysis_chunk_overlap_lines: int = 3
    ollama_timeout_seconds: int = 180

    transcription_provider: str = "cloudflare"

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_whisper_model: str = (
        "@cf/openai/whisper-large-v3-turbo"
    )
    cloudflare_whisper_language: str = ""
    cloudflare_whisper_vad_filter: bool = True
    cloudflare_whisper_beam_size: int = 5
    cloudflare_whisper_condition_on_previous_text: bool = True
    cloudflare_whisper_initial_prompt: str = ""
    cloudflare_timeout_seconds: int = 300
    cloudflare_chunk_seconds: int = 300
    cloudflare_chunk_overlap_seconds: int = 8
    cloudflare_parallel_workers: int = 2
    cloudflare_fallback_to_local: bool = True

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = 6
    whisper_num_workers: int = 1
    whisper_beam_size: int = 3
    whisper_vad_filter: bool = True
    whisper_condition_on_previous_text: bool = True
    whisper_language: str = ""

    huggingface_token: str = ""
    pyannote_model: str = (
        "pyannote/speaker-diarization-community-1"
    )
    pyannote_device: str = "cpu"
    pyannote_cpu_threads: int = 6

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def normalized_transcription_provider(self) -> str:
        provider = self.transcription_provider.strip().lower()

        if provider not in {"cloudflare", "local"}:
            raise ValueError(
                "TRANSCRIPTION_PROVIDER must be "
                "'cloudflare' or 'local'."
            )

        return provider

    @property
    def cloudflare_ai_base_url(self) -> str:
        account_id = self.cloudflare_account_id.strip()

        if not account_id:
            return ""

        return (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/run"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
