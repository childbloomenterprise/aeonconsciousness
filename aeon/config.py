from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    aeon_runtime_mode: str = "local"
    aeon_runtime_dir: Path = Path("runtime")
    aeon_model_provider: str = "mock"
    aeon_model_name: str = "claude-sonnet-4-20250514"
    aeon_mock_seed: int = 42
    aeon_workspace_capacity: int = 3
    aeon_max_cycles: int = 3
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    aeon_observer_signing_key: str = "local-development-key"


@lru_cache
def get_settings() -> Settings:
    return Settings()
