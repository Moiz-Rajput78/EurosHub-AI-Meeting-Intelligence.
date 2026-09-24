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

    # Ollama Cloud analysis.
    ollama_mode: str = "cloud"
    ollama_base_url: str = "https://ollama.com"
    ollama_api_key: str = ""
    ollama_model: str = "gemma4:cloud"
    analysis_chunk_chars: int = 12000
    analysis_chunk_overlap_lines: int = 3
    ollama_timeout_seconds: int = 180

    # Transcription provider.
    transcription_provider: str = "cloudflare"

    # Cloudflare Workers AI transcription.
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_whisper_model: str = (
        "@cf/openai/whisper-large-v3-turbo"
    )

    # Blank enables automatic language handling in the Cloudflare
    # service. This is the recommended setting for English, Urdu
    # and mixed-language meetings.
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

    # Local Faster Whisper fallback.
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_cpu_threads: int = 6
    whisper_num_workers: int = 1
    whisper_beam_size: int = 3
    whisper_vad_filter: bool = True
    whisper_condition_on_previous_text: bool = True
    whisper_language: str = ""

    # Diarization provider.
    #
    # Supported values:
    # - deepgram
    # - local
    diarization_provider: str = "deepgram"

    # Deepgram cloud diarization.
    deepgram_api_key: str = ""
    deepgram_api_url: str = (
        "https://api.deepgram.com/v1/listen"
    )
    deepgram_model: str = "nova-3"

    # Deepgram currently recommends `diarize_model=latest`
    # for new batch diarization integrations.
    deepgram_diarize_model: str = "latest"

    # Leave blank to use Deepgram language detection.
    # Set `en` for known English-only audio or `ur` for
    # known Urdu-only audio.
    deepgram_language: str = ""

    deepgram_timeout_seconds: int = 600

    # Merge consecutive words from the same detected speaker when
    # the gap between them is small. This produces compact speaker
    # turns while retaining accurate transcript-to-speaker mapping.
    deepgram_turn_merge_gap_seconds: float = 1.0

    # Preserve the existing Pyannote implementation as a fallback.
    diarization_fallback_to_local: bool = True

    # Local Pyannote fallback.
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
        return Path(
            self.upload_dir
        ).resolve()

    @property
    def normalized_transcription_provider(
        self,
    ) -> str:
        provider = (
            self.transcription_provider
            .strip()
            .lower()
        )

        if provider not in {
            "cloudflare",
            "local",
        }:
            raise ValueError(
                "TRANSCRIPTION_PROVIDER must be "
                "'cloudflare' or 'local'."
            )

        return provider

    @property
    def normalized_diarization_provider(
        self,
    ) -> str:
        provider = (
            self.diarization_provider
            .strip()
            .lower()
        )

        if provider not in {
            "deepgram",
            "local",
        }:
            raise ValueError(
                "DIARIZATION_PROVIDER must be "
                "'deepgram' or 'local'."
            )

        return provider

    @property
    def cloudflare_ai_base_url(
        self,
    ) -> str:
        account_id = (
            self.cloudflare_account_id
            .strip()
        )

        if not account_id:
            return ""

        return (
            "https://api.cloudflare.com/"
            f"client/v4/accounts/{account_id}/ai/run"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
