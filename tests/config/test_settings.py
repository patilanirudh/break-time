import pytest

from breaktime.config import settings as settings_module
from breaktime.config.settings import BreakTimeSettings


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "CONFIG_FILE", tmp_path / "config.json")


def test_load_returns_defaults_when_no_file_exists():
    settings = BreakTimeSettings.load()
    assert settings.continuous_time_threshold_seconds == 1200
    assert settings.verified_break_enabled is True
    assert settings.crash_reporting_opt_in is False


def test_save_then_load_round_trips_values():
    settings = BreakTimeSettings(continuous_time_threshold_seconds=600, auto_start_enabled=False)
    settings.save()

    reloaded = BreakTimeSettings.load()
    assert reloaded.continuous_time_threshold_seconds == 600
    assert reloaded.auto_start_enabled is False


def test_load_falls_back_to_defaults_on_corrupt_file():
    settings_module.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    settings_module.CONFIG_FILE.write_text("not valid json", encoding="utf-8")

    settings = BreakTimeSettings.load()
    assert settings.continuous_time_threshold_seconds == 1200


def test_field_validation_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        BreakTimeSettings(continuous_time_threshold_seconds=10)  # below the ge=60 floor
