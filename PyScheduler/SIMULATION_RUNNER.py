from abc import ABC, abstractmethod
from typing import List
# TODO: Импорты ядра (BS_MODULE, UE_MODULE, SCHEDULER) добавим позже

class ISimulationRunner(ABC):
    @abstractmethod
    def run(self, spec) -> str: ...
    @abstractmethod
    def list_scenarios(self) -> List[str]: ...
    @abstractmethod
    def list_algorithms(self) -> List[str]: ...
    # ...

class SimulationRunner(ISimulationRunner):
    def run(self, spec) -> str:
        # TODO: Сборка сценария (BS, UE, Scheduler)
        return spec.stats.file_prefix

    def list_scenarios(self) -> List[str]:
        return ["simple", "qos"]

    def list_algorithms(self) -> List[str]:
        return [] # TODO: Делегировать в SCHEDULER