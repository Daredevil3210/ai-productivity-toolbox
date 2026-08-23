from __future__ import annotations

import pytest

from toolbox.config import ConfigurationError, Settings


def clear_model_environment(monkeypatch) -> None:
    for name in (
        "MODEL_PROVIDER",
        "MODEL_NAME",
        "MODEL_API_KEY",
        "MODEL_BASE_URL",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "MAX_TOOL_ROUNDS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_deepseek_requires_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    with pytest.raises(ConfigurationError):
        Settings.from_env(env_path=tmp_path / ".env")


def test_ollama_uses_default_local_url(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    clear_model_environment(monkeypatch)
    monkeypatch.setenv("MODEL_PROVIDER", "ollama")
    monkeypatch.setenv("MODEL_NAME", "deepseek-r1:1.5b")
    settings = Settings.from_env(env_path=tmp_path / ".env")
    assert settings.api_key is None
    assert settings.base_url == "http://localhost:11434"
