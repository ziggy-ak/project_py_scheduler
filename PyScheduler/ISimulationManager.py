"""
ISimulationManager.py — ABC-интерфейс для SimulationManager.

Три метода, которые дёргает API:
  - configure(**config)     — сборка ядра по конфигу
  - start_simulation()      — запуск TTI-цикла
  - get_longterm_fairness() — Jain's Fairness Index
"""

from abc import ABC, abstractmethod
from typing import Optional


class ISimulationManager(ABC):
    """Интерфейс менеджера симуляции для API-модуля."""

    @abstractmethod
    def configure(self, **config) -> None:
        """
        Собрать ядро по конфигу.

        Принимает распакованный dict из dataclasses.asdict(SimulationSpec).
        Создаёт BaseStation, UECollection, связывает, настраивает
        планировщик, трафик, интервалы, карту.
        """
        ...

    @abstractmethod
    def start_simulation(self) -> None:
        """
        Запустить TTI-цикл.

        После возврата файлы с результатами существуют (контракт с API).
        Формат файлов — публичный контракт со Stats Manager (согласуется).
        """
        ...
