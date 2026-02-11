"""Unit tests for Settings."""

import os
import tempfile

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from mpyutils import Settings


class TestTomlSettings:
    """Tests for Settings class."""

    def test_default_values_only(self, monkeypatch: pytest.MonkeyPatch):
        """Test settings with only default values, no TOML or env."""

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            host: str = "localhost"
            port: int = 8080

        config = Config()
        assert config.host == "localhost"
        assert config.port == 8080

    def test_toml_file_loading(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading settings from TOML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('host = "toml-host"\nport = 3000\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                host: str = "localhost"
                port: int = 8080

            config = Config()
            assert config.host == "toml-host"
            assert config.port == 3000
        finally:
            os.unlink(toml_path)

    def test_env_override_toml(self, monkeypatch: pytest.MonkeyPatch):
        """Test that environment variables override TOML values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('host = "toml-host"\nport = 3000\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)
            monkeypatch.setenv("TEST_HOST", "env-host")

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                host: str = "localhost"
                port: int = 8080

            config = Config()
            assert config.host == "env-host"  # From env
            assert config.port == 3000  # From TOML
        finally:
            os.unlink(toml_path)

    def test_partial_toml_partial_env(self, monkeypatch: pytest.MonkeyPatch):
        """Test that partial TOML + partial env works together."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('host = "toml-host"\n')  # port is missing
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)
            monkeypatch.setenv("TEST_PORT", "9000")

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                host: str  # required
                port: int  # required

            config = Config()  # type: ignore[arg-type]
            assert config.host == "toml-host"  # From TOML
            assert config.port == 9000  # From env
        finally:
            os.unlink(toml_path)

    def test_missing_required_field_raises_error(self, monkeypatch: pytest.MonkeyPatch):
        """Test that missing required fields raise ValidationError."""

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            required_field: str  # No default

        with pytest.raises(ValidationError):
            Config()  # type: ignore[arg-type]

    def test_missing_toml_file_raises_error(self, monkeypatch: pytest.MonkeyPatch):
        """Test that missing TOML file raises FileNotFoundError."""
        monkeypatch.setenv("TEST_CONFIG_FILE", "/nonexistent/config.toml")

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            host: str = "localhost"

        with pytest.raises(FileNotFoundError):
            Config()

    def test_no_toml_file_uses_defaults_and_env(self, monkeypatch: pytest.MonkeyPatch):
        """Test that without TOML file, defaults and env vars work."""
        monkeypatch.setenv("TEST_HOST", "env-host")

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            host: str = "localhost"
            port: int = 8080

        config = Config()
        assert config.host == "env-host"  # From env
        assert config.port == 8080  # From default

    def test_boolean_from_env(self, monkeypatch: pytest.MonkeyPatch):
        """Test boolean type coercion from environment variables."""
        monkeypatch.setenv("TEST_DEBUG", "true")

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            debug: bool = False

        config = Config()
        assert config.debug is True

    def test_integer_from_env(self, monkeypatch: pytest.MonkeyPatch):
        """Test integer type coercion from environment variables."""
        monkeypatch.setenv("TEST_PORT", "3000")

        class Config(Settings):
            model_config = SettingsConfigDict(env_prefix="TEST_")
            port: int = 8080

        config = Config()
        assert config.port == 3000
        assert isinstance(config.port, int)

    def test_init_kwargs_override_all(self, monkeypatch: pytest.MonkeyPatch):
        """Test that init kwargs have highest priority."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('host = "toml-host"\nport = 3000\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)
            monkeypatch.setenv("TEST_HOST", "env-host")

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                host: str = "localhost"
                port: int = 8080

            config = Config(host="init-host", port=5000)
            assert config.host == "init-host"  # From init kwarg
            assert config.port == 5000  # From init kwarg
        finally:
            os.unlink(toml_path)

    def test_nested_toml_to_nested_model(self, monkeypatch: pytest.MonkeyPatch):
        """Test that nested TOML sections map to nested pydantic models."""
        from pydantic import BaseModel

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[database]\nhost = "prod-db"\nport = 3306\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                database: DatabaseConfig = DatabaseConfig()

            config = Config()
            assert config.database.host == "prod-db"
            assert config.database.port == 3306
        finally:
            os.unlink(toml_path)

    def test_nested_toml_partial_override(self, monkeypatch: pytest.MonkeyPatch):
        """Test partial nested TOML section with defaults."""
        from pydantic import BaseModel

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[database]\nhost = "prod-db"\n')  # port not specified
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                database: DatabaseConfig = DatabaseConfig()

            config = Config()
            assert config.database.host == "prod-db"
            assert config.database.port == 5432  # Default from nested model
        finally:
            os.unlink(toml_path)

    def test_deeply_nested_toml(self, monkeypatch: pytest.MonkeyPatch):
        """Test deeply nested TOML sections."""
        from pydantic import BaseModel

        class CacheConfig(BaseModel):
            enabled: bool = True
            ttl: int = 3600

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432
            cache: CacheConfig = CacheConfig()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[database]\nhost = "db-server"\n[database.cache]\nenabled = false\nttl = 1800\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                database: DatabaseConfig = DatabaseConfig()

            config = Config()
            assert config.database.host == "db-server"
            assert config.database.cache.enabled is False
            assert config.database.cache.ttl == 1800
        finally:
            os.unlink(toml_path)

    def test_multiple_nested_sections(self, monkeypatch: pytest.MonkeyPatch):
        """Test multiple nested TOML sections."""
        from pydantic import BaseModel

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        class RedisConfig(BaseModel):
            host: str = "localhost"
            port: int = 6379

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write('[database]\nhost = "db-server"\n[redis]\nhost = "redis-server"\nport = 6380\n')
            toml_path = f.name

        try:
            monkeypatch.setenv("TEST_CONFIG_FILE", toml_path)

            class Config(Settings):
                model_config = SettingsConfigDict(env_prefix="TEST_")
                database: DatabaseConfig = DatabaseConfig()
                redis: RedisConfig = RedisConfig()

            config = Config()
            assert config.database.host == "db-server"
            assert config.database.port == 5432  # Default
            assert config.redis.host == "redis-server"
            assert config.redis.port == 6380
        finally:
            os.unlink(toml_path)
