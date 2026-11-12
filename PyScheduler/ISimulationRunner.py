"""
ISimulationRunner.py — контракт для сборщика сценариев.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ISimulationRunner(ABC):
    @abstractmethod
    def run(self, spec: Any) -> str:
        """Собирает сценарий, запускает SM, возвращает file_prefix."""
        ...

    @abstractmethod
    def list_scenarios(self) -> List[str]: ...

    @abstractmethod
    def list_algorithms(self) -> List[str]: ...

    @abstractmethod
    def list_channel_models(self) -> List[str]: ...

    @abstractmethod
    def list_traffic_models(self) -> List[str]: ...

    @abstractmethod
    def list_mobility_models(self) -> List[str]: ...