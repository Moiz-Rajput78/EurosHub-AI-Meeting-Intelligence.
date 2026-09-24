from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = (
        "Meeting Intelligence"
    )

    app_env: str = "development"

    debug: bool = True

    host: str = "127.0.0.1"

    port: int = 8000

    database_url: str = (
        "sqlite:///./meetings.db"
    )

    upload_dir: str = "./uploads"

    max_upload_size_mb: int = 500

    ollama_mode: str = "cloud"

    ollama_base_url: str = (
        "https://ollama.com"
    )

    ollama_api_key: str = ""

    ollama_model: str = (
        "gemma4:cloud"
    )

    analysis_chunk_chars: int = 12000

    analysis_chunk_overlap_lines: int = 3

    ollama_timeout_seconds: int = 180

    # Keep the accurate "small" multilingual model by default.
    # The model remains configurable through .env.
    whisper_model: str = "small"

    whisper_device: str = "cpu"

    whisper_compute_type: str = "int8"

    # 6 physical cores is a good starting point for the
    # Ryzen 5 7530U while leaving Windows responsive.
    whisper_cpu_threads: int = 6

    # A single worker is appropriate for the current sequential
    # meeting-processing pipeline and avoids duplicated CPU load.
    whisper_num_workers: int = 1

    # Beam 3 is a balanced setting: faster than the previous
    # beam 5 while retaining better decoding quality than greedy
    # beam 1.
    whisper_beam_size: int = 3

    whisper_vad_filter: bool = True

    whisper_condition_on_previous_text: bool = True

    # Leave blank for automatic language detection.
    # Set WHISPER_LANGUAGE=en only when you know the meeting
    # is English and want to skip language detection.
    whisper_language: str = ""

    huggingface_token: str = ""

    pyannote_model: str = (
        "pyannote/"
        "speaker-diarization-community-1"
    )

    pyannote_device: str = "cpu"

    # Match the laptop's 6 physical CPU cores by default.
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
        return Path(
            self.upload_dir
        ).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
