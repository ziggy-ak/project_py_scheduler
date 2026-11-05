"""
tests/test_api_config.py — валидация конфигов API_MODULE.

Покрытие:
  - SimulationSpec: duration, update_interval, mobility_interval, channel_interval
  - UEConfig: count, ue_class, границы карты (x, y)

Валидация BSConfig, SchedulerConfig, StatsConfig — неделя 9.

Запуск:
    cd PyScheduler
    python -m pytest tests/test_api_config.py -v
"""

import pytest

from API_MODULE import SimulationSpec, UEConfig


def test_duration_positive():
    spec = SimulationSpec(duration=5000)
    assert spec.duration == 5000


def test_update_interval_positive():
    spec = SimulationSpec(update_interval=1)
    assert spec.update_interval == 1


def test_mobility_interval_positive():
    spec = SimulationSpec(mobility_interval=500)
    assert spec.mobility_interval == 500


def test_channel_interval_positive():
    spec = SimulationSpec(channel_interval=1)
    assert spec.channel_interval == 1


def test_ue_count_positive():
    spec = SimulationSpec(ues=UEConfig(count=5))
    assert spec.ues.count == 5


def test_ue_class_valid():
    for cls in ["random", "pedestrian", "cyclist", "car"]:
        spec = SimulationSpec(ues=UEConfig(ue_class=cls))
        assert spec.ues.ue_class == cls


def test_x_borders_valid():
    spec = SimulationSpec(ues=UEConfig(x_min=-100, x_max=100))
    assert spec.ues.x_min < spec.ues.x_max


def test_y_borders_valid():
    spec = SimulationSpec(ues=UEConfig(y_min=-100, y_max=100))
    assert spec.ues.y_min < spec.ues.y_max

def test_duration_negative_raises():
    with pytest.raises(ValueError, match="Длительность симуляции должна быть > 0"):
        SimulationSpec(duration=-100)


def test_duration_zero_raises():
    with pytest.raises(ValueError, match="Длительность симуляции должна быть > 0"):
        SimulationSpec(duration=0)


def test_ue_count_zero_raises():
    with pytest.raises(ValueError, match="Количество UE должно быть > 0"):
        SimulationSpec(ues=UEConfig(count=0))


def test_ue_class_unknown_raises():
    with pytest.raises(ValueError, match="Неизвестный ue_class"):
        SimulationSpec(ues=UEConfig(ue_class="spaceship"))


def test_x_borders_invalid_raises():
    with pytest.raises(ValueError, match="x_min должен быть < x_max"):
        SimulationSpec(ues=UEConfig(x_min=100, x_max=100))


def test_y_borders_invalid_raises():
    with pytest.raises(ValueError, match="y_min должен быть < y_max"):
        SimulationSpec(ues=UEConfig(y_min=500, y_max=-500))