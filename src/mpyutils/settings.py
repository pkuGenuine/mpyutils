"""Settings utility that supports TOML config file and environment variables."""

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from pydantic_settings.sources import InitSettingsSource


class TomlSettingsSource(InitSettingsSource):
    """Custom settings source that reads from TOML file."""

    def __init__(self, settings_cls: type[BaseSettings], toml_path: Path | None):
        self.toml_path = toml_path
        toml_data = self._load_toml()
        super().__init__(settings_cls, toml_data)

    def _load_toml(self) -> dict[str, Any]:
        """Load TOML file contents."""
        if self.toml_path is None:
            return {}
        if not self.toml_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.toml_path}")
        with open(self.toml_path, "rb") as f:
            return tomllib.load(f)


class Settings(BaseSettings):
    """
    Settings class that supports TOML config file + environment variables.

    Precedence (highest to lowest):
        1. Init kwargs
        2. Environment variables ({PREFIX}FIELD_NAME)
        3. TOML config file (path from {PREFIX}CONFIG_FILE env var)
        4. Default values in class definition

    Example:
        ```python
        from pydantic_settings import SettingsConfigDict
        from mpyutils import Settings

        class AppConfig(Settings):
            model_config = SettingsConfigDict(env_prefix="APP_")

            database_host: str  # required
            database_port: int = 5432
            debug: bool = False

        # Set APP_CONFIG_FILE=/path/to/config.toml
        # Set APP_DATABASE_HOST=prod-server (overrides TOML)
        config = AppConfig()
        ```
    """

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Configure settings sources with TOML support."""
        # Get env_prefix from model_config
        env_prefix = cls.model_config.get("env_prefix", "")
        config_file_env = f"{env_prefix}CONFIG_FILE"
        toml_path_str = os.environ.get(config_file_env)
        toml_path = Path(toml_path_str) if toml_path_str else None

        # Order (highest to lowest priority - earlier sources take precedence):
        # 1. Init kwargs (highest priority)
        # 2. Environment variables
        # 3. TOML file (lowest priority)
        return (
            init_settings,
            env_settings,
            TomlSettingsSource(settings_cls, toml_path),
        )
