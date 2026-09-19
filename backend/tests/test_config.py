"""Configuration behavior tests."""

from app.core.config import Environment, Settings, get_settings


def test_cors_origins_are_normalized() -> None:
    settings = Settings(cors_origins="https://one.example, https://two.example, ")

    assert settings.cors_origin_list == ["https://one.example", "https://two.example"]


def test_production_flag() -> None:
    assert Settings(environment=Environment.PRODUCTION).is_production is True
    assert Settings(environment=Environment.DEVELOPMENT).is_production is False


def test_settings_factory_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
