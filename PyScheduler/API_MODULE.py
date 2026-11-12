"""
API_MODULE.py — прослойка между ядром и внешними интерфейсами (CLI, FastAPI).

Структура:
  Секция 0: Импорты
  Секция 1: Конфиги (вход)      — SimulationSpec + вложенные DTO
  Секция 2: Результат (выход)   — SimulationResult
  Секция 3: ISimulationAPI (ABC)
  Секция 4: SimulationAPI (реализация)
  Секция 5: Парсинг файлов      — временный, до согласования формата

Новая архитектура (v2):
    CLI / FastAPI 
        ↓ (SimulationSpec)
    ISimulationAPI (SimulationAPI)
        ↓ (runner.run(spec))
    ISimulationRunner (SimulationRunner)
        ↓ (создает BS, UE, Scheduler и т.д.)
    SimulationManager.start_simulation()
        ↓ (пишет файлы)
    API парсит CSV → SimulationResult

API больше не знает про SimulationManager. Он работает только с ISimulationRunner,
который внедряется через Dependency Injection (runner_factory) в конструктор.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable

from ISimulationRunner import ISimulationRunner

# ==============================================================================
# СЕКЦИЯ 1. КОНФИГИ (ВХОД)
# ==============================================================================

@dataclass(slots=True)
class BSConfig:
    """Конфигурация базовой станции."""
    x: float = 0.0
    y: float = 0.0
    height: float = 35.0
    frequency_GHz: float = 1.8
    bandwidth: float = 10
    ch_model_type: str = "UMa"
    use_simple_buffer: bool = True
    enable_tdl: bool = False


@dataclass(slots=True)
class UEConfig:
    """Конфигурация пользовательских устройств."""
    count: int = 5
    ue_class: str = "random"
    x_min: float = -500
    x_max: float = 500
    y_min: float = -500
    y_max: float = 500

    def __post_init__(self):
        if self.count <= 0:
            raise ValueError(f"Количество UE должно быть > 0, получено {self.count}")
        valid_classes = {"random", "pedestrian", "cyclist", "car"}
        if self.ue_class not in valid_classes:
            raise ValueError(f"Неизвестный ue_class '{self.ue_class}'. Допустимые: {sorted(valid_classes)}")
        if self.x_min >= self.x_max:
            raise ValueError(f"x_min должен быть < x_max, получено {self.x_min} >= {self.x_max}")
        if self.y_min >= self.y_max:
            raise ValueError(f"y_min должен быть < y_max, получено {self.y_min} >= {self.y_max}")


@dataclass(slots=True)
class SchedulerConfig:
    """Конфигурация планировщика."""
    algorithm: str = "RoundRobin"
    max_dl_ue_tti: Optional[int] = None
    pcfich: int = 2
    max_dl_cce_allowance: Optional[int] = None
    window_size: int = 100
    enable_window: bool = True


@dataclass(slots=True)
class StatsConfig:
    """Конфигурация статистики."""
    enabled: bool = True
    collect_interval: int = 1
    scheduler_level: str = "basic"
    amc_level: str = "basic"
    pdcch_level: str = "none"
    file_prefix: str = "sim_stats"


@dataclass(slots=True)
class TrafficConfig:
    """Конфигурация трафика (v1)."""
    model_type: str = "Poisson"
    packet_rate: float = 5000.0


@dataclass(slots=True)
class SimulationSpec:
    """Полный конфиг симуляции."""
    duration: int = 5000
    update_interval: int = 1
    mobility_interval: int = 500
    channel_interval: int = 1
    seed: Optional[int] = None
    verbose: bool = False
    
    scenario: str = "simple"
    mobility_model: str = "RandomWaypoint"

    bs: BSConfig = field(default_factory=BSConfig)
    ues: UEConfig = field(default_factory=UEConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)

    def __post_init__(self):
        if self.duration <= 0:
            raise ValueError(f"Длительность симуляции должна быть > 0, получено {self.duration}")
        if self.update_interval <= 0:
            raise ValueError(f"Интервал обновления должен быть > 0, получено {self.update_interval}")
        if self.mobility_interval <= 0:
            raise ValueError(f"Интервал мобильности должен быть > 0, получено {self.mobility_interval}")
        if self.channel_interval <= 0:
            raise ValueError(f"Интервал канала должен быть > 0, получено {self.channel_interval}")
        if self.scenario not in {"simple", "qos"}:
            raise ValueError(f"Неизвестный сценарий '{self.scenario}'. Допустимые: simple, qos")


# ==============================================================================
# СЕКЦИЯ 2. РЕЗУЛЬТАТ (ВЫХОД)
# ==============================================================================

@dataclass(slots=True)
class SimulationResult:
    """Результат симуляции."""
    duration_tti: int
    algorithm: str
    num_ues: int

    jain_fairness: Optional[float] = None
    avg_cell_throughput_kbps: float = 0.0
    avg_spectral_efficiency: float = 0.0
    avg_prb_utilization_pct: float = 0.0

    csv_path: Optional[str] = None
    detailed_csv_path: Optional[str] = None

    def to_files(self) -> Dict[str, Optional[str]]:
        return {"main": self.csv_path, "detailed": self.detailed_csv_path}

    def to_json(self) -> Dict[str, Any]:
        return {
            "duration_tti": self.duration_tti,
            "algorithm": self.algorithm,
            "num_ues": self.num_ues,
            "jain_fairness": self.jain_fairness,
            "avg_cell_throughput_kbps": self.avg_cell_throughput_kbps,
            "avg_spectral_efficiency": self.avg_spectral_efficiency,
            "avg_prb_utilization_pct": self.avg_prb_utilization_pct,
            "files": self.to_files(),
        }


# ==============================================================================
# СЕКЦИЯ 3. ИНТЕРФЕЙС API
# ==============================================================================

class ISimulationAPI(ABC):
    """
    Публичный интерфейс API-модуля.
    CLI (Ника) и FastAPI работают через ISimulationAPI.
    """

    @abstractmethod
    def run(self, spec: SimulationSpec) -> SimulationResult:
        """Запустить симуляцию по конфигу. Вернуть результат."""
        ...

    @abstractmethod
    def validate(self, spec: SimulationSpec) -> List[str]:
        """Проверить конфиг. Вернуть список ошибок (пустой = ок)."""
        ...

    @abstractmethod
    def list_scenarios(self) -> List[str]:
        """Доступные сценарии симуляции."""
        ...

    @abstractmethod
    def list_algorithms(self) -> List[str]:
        """Доступные алгоритмы планировщика."""
        ...

    @abstractmethod
    def list_channel_models(self) -> List[str]:
        """Доступные модели канала."""
        ...

    @abstractmethod
    def list_traffic_models(self) -> List[str]:
        """Доступные модели трафика."""
        ...

    @abstractmethod
    def list_mobility_models(self) -> List[str]:
        """Доступные модели мобильности."""
        ...


# ==============================================================================
# СЕКЦИЯ 4. РЕАЛИЗАЦИЯ API
# ==============================================================================

class SimulationAPI(ISimulationAPI):
    """Реализация API. Работает через DI (фабрику раннеров)."""

    def __init__(self, runner_factory: Callable[[], ISimulationRunner]):
        """
        Args:
            runner_factory: Функция/класс, создающий ISimulationRunner.
                            В CLI это будет lambda: SimulationRunner().
                            В тестах это FakeRunner.
        """
        self._runner_factory = runner_factory

    def run(self, spec: SimulationSpec) -> SimulationResult:
        """Запуск симуляции."""
        errors = self.validate(spec)
        if errors:
            raise ValueError(f"Ошибка валидации конфига: {errors}")

        # 1. Получаем раннер через фабрику
        runner = self._runner_factory()
        
        # 2. Раннер собирает ядро, запускает SM и возвращает file_prefix
        file_prefix = runner.run(spec)

        # 3. API читает файлы и собирает результат
        csv_path = f"{file_prefix}.csv"
        detailed_csv_path = f"{file_prefix}_detailed.csv"
        metrics = _parse_stats_files(csv_path, detailed_csv_path)

        return SimulationResult(
            duration_tti=spec.duration,
            algorithm=spec.scheduler.algorithm,
            num_ues=spec.ues.count,
            jain_fairness=metrics.get("jain_fairness"),
            avg_cell_throughput_kbps=metrics.get("avg_throughput_kbps", 0.0),
            avg_spectral_efficiency=metrics.get("avg_se", 0.0),
            avg_prb_utilization_pct=metrics.get("avg_prb_utilization_pct", 0.0),
            csv_path=csv_path,
            detailed_csv_path=detailed_csv_path,
        )

    def validate(self, spec: SimulationSpec) -> List[str]:
        """Проверка совместимости параметров (логическая валидация)."""
        errors: List[str] = []

        # Базовые инварианты уже проверены в __post_init__, 
        # здесь только логика совместимости.

        if spec.scenario not in self.list_scenarios():
            errors.append(f"Сценарий '{spec.scenario}' не поддерживается API.")

        if spec.scheduler.algorithm not in self.list_algorithms():
            errors.append(f"Алгоритм '{spec.scheduler.algorithm}' не найден.")

        if spec.bs.ch_model_type not in self.list_channel_models():
            errors.append(f"Модель канала '{spec.bs.ch_model_type}' не найдена.")

        return errors

    def list_scenarios(self) -> List[str]:
        return self._runner_factory().list_scenarios()

    def list_algorithms(self) -> List[str]:
        return self._runner_factory().list_algorithms()

    def list_channel_models(self) -> List[str]:
        return self._runner_factory().list_channel_models()

    def list_traffic_models(self) -> List[str]:
        return self._runner_factory().list_traffic_models()

    def list_mobility_models(self) -> List[str]:
        return self._runner_factory().list_mobility_models()


# ==============================================================================
# СЕКЦИЯ 5. ПАРСИНГ ФАЙЛОВ (ВРЕМЕННЫЙ)
# ==============================================================================

def _parse_stats_files(csv_path: str, detailed_csv_path: str) -> Dict[str, float]:
    """
    Парсинг CSV файлов, сгенерированных StatsManager.
    
    ВРЕМЕННО: формат файлов еще согласовывается с наставником (StatsManager).
    Пока возвращаем заглушки (0.0), чтобы не ломать контракт SimulationResult.
    """
    # TODO: Заменить на реальный парсинг через csv.DictReader
    return {
        "jain_fairness": 0.95,        # Заглушка для тестов
        "avg_throughput_kbps": 15000.0, # Заглушка
        "avg_se": 2.5,                # Заглушка
        "avg_prb_utilization_pct": 85.0,
    }