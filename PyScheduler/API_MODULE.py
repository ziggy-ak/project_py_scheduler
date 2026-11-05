"""
API_MODULE.py

Структура:
  Секция 0: Импорты
  Секция 1: Конфиги (вход)      — SimulationSpec + вложенные
  Секция 2: Результат (выход)   — SimulationResult
  Секция 3: ISimulationAPI (ABC)
  Секция 4: SimulationAPI (реализация)
  Секция 5: Парсинг файлов      — временный, до согласования формата

Контракт:
    CLI / FastAPI → ISimulationAPI → SimulationAPI
                                       ↓ asdict(spec)
                                    ISimulationManager.configure(**config)
                                       ↓
                                    ISimulationManager.start_simulation()
                                       ↓ (файлы созданы)
                                    _parse_stats_files(csv) → SimulationResult

Внимание: run() зависит от SimulationManager.configure() и
get_longterm_fairness(). Оба метода — неделя 9 (см. TODO).
Пока не реализованы — run() бросает NotImplementedError с понятным
сообщением. validate() и конфиги работают независимо.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import csv

from SIMULATION_MANAGER import ISimulationManager, SimulationManager


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
            raise ValueError(
                f"Количество UE должно быть > 0, получено {self.count}"
            )

        valid_classes = {"random", "pedestrian", "cyclist", "car"}
        if self.ue_class not in valid_classes:
            raise ValueError(
                f"Неизвестный ue_class '{self.ue_class}'. "
                f"Допустимые: {sorted(valid_classes)}"
            )

        if self.x_min >= self.x_max:
            raise ValueError(
                f"x_min должен быть < x_max, получено "
                f"{self.x_min} >= {self.x_max}"
            )
        if self.y_min >= self.y_max:
            raise ValueError(
                f"y_min должен быть < y_max, получено "
                f"{self.y_min} >= {self.y_max}"
            )


@dataclass(slots=True)
class SchedulerConfig:
    """Конфигурация планировщика. Валидация — неделя 9."""
    algorithm: str = "RoundRobin"
    max_dl_ue_tti: Optional[int] = None
    pcfich: int = 2
    max_dl_cce_allowance: Optional[int] = None
    window_size: int = 100
    enable_window: bool = True


@dataclass(slots=True)
class StatsConfig:
    """Конфигурация статистики. Валидация — неделя 9."""
    enabled: bool = True
    collect_interval: int = 1
    scheduler_level: str = "basic"
    amc_level: str = "basic"
    pdcch_level: str = "none"
    file_prefix: str = "sim_stats"


@dataclass(slots=True)
class SimulationSpec:
    """Полный конфиг симуляции."""
    duration: int = 5000
    update_interval: int = 1
    mobility_interval: int = 500
    channel_interval: int = 1
    seed: Optional[int] = None
    verbose: bool = False

    bs: BSConfig = field(default_factory=BSConfig)
    ues: UEConfig = field(default_factory=UEConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)

    def __post_init__(self):
        if self.duration <= 0:
            raise ValueError(
                f"Длительность симуляции должна быть > 0, "
                f"получено {self.duration}"
            )
        if self.update_interval <= 0:
            raise ValueError(
                f"Интервал обновления должен быть > 0, "
                f"получено {self.update_interval}"
            )
        if self.mobility_interval <= 0:
            raise ValueError(
                f"Интервал мобильности должен быть > 0, "
                f"получено {self.mobility_interval}"
            )
        if self.channel_interval <= 0:
            raise ValueError(
                f"Интервал канала должен быть > 0, "
                f"получено {self.channel_interval}"
            )


@dataclass(slots=True)
class SimulationResult:
    """Результат симуляции."""
    duration_tti: int
    algorithm: str
    num_ues: int

    jain_fairness: Optional[float] = None
    avg_cell_throughput_kbps: float = 0.0
    avg_spectral_efficiency: float = 0.0

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
            "files": self.to_files(),
        }

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


class SimulationAPI(ISimulationAPI):
    """Реализация API. Тонкая прослойка: asdict → configure → start → parse."""

    def run(self, spec: SimulationSpec) -> SimulationResult:
        """
        Запустить симуляцию и вернуть результат.

        Зависит от SimulationManager.configure() и
        SimulationManager.get_longterm_fairness(). Пока не реализованы —
        бросает NotImplementedError с понятным сообщением.
        """
        config_dict = asdict(spec)

        sim: ISimulationManager = SimulationManager()

        if not hasattr(sim, "configure") or not callable(
            getattr(sim, "configure", None)
        ):
            raise NotImplementedError(
                "SimulationManager.configure(**config) ещё не реализован. "
                "Это ожидаемо: API-скелет готов, backend — неделя 9. "
                "См. TODO в отчёте."
            )

        sim.configure(**config_dict)
        sim.start_simulation()

        # После возврата start_simulation() файлы существуют (контракт).
        csv_path = f"{spec.stats.file_prefix}.csv"
        detailed_csv_path = f"{spec.stats.file_prefix}_detailed.csv"

        metrics = _parse_stats_files(csv_path, detailed_csv_path)

        jain = None
        if hasattr(sim, "get_longterm_fairness") and callable(
            getattr(sim, "get_longterm_fairness", None)
        ):
            jain = sim.get_longterm_fairness()

        return SimulationResult(
            duration_tti=spec.duration,
            algorithm=spec.scheduler.algorithm,
            num_ues=spec.ues.count,
            jain_fairness=jain,
            avg_cell_throughput_kbps=metrics["avg_throughput_kbps"],
            avg_spectral_efficiency=metrics["avg_se"],
            csv_path=csv_path,
            detailed_csv_path=detailed_csv_path,
        )

    def validate(self, spec: SimulationSpec) -> List[str]:
        """
        Проверить конфиг. Возвращает список ошибок (пустой = ок).

        На неделе 9 добавится валидация BSConfig, SchedulerConfig,
        StatsConfig через __post_init__ (или здесь).
        """
        errors: List[str] = []

        if spec.duration <= 0:
            errors.append("Длительность симуляции должна быть > 0")
        if spec.ues.count <= 0:
            errors.append("Количество UE должно быть > 0")

        valid_bandwidths = [1.4, 3, 5, 10, 15, 20]
        if spec.bs.bandwidth not in valid_bandwidths:
            errors.append(
                f"bs.bandwidth должен быть одним из {valid_bandwidths}, "
                f"получено {spec.bs.bandwidth}"
            )

        if spec.scheduler.algorithm not in self.list_algorithms():
            errors.append(
                f"scheduler.algorithm '{spec.scheduler.algorithm}' "
                f"не входит в {self.list_algorithms()}"
            )

        if spec.bs.ch_model_type not in self.list_channel_models():
            errors.append(
                f"bs.ch_model_type '{spec.bs.ch_model_type}' "
                f"не входит в {self.list_channel_models()}"
            )

        return errors

    def list_algorithms(self) -> List[str]:
        """
        Доступные алгоритмы планировщика.

        ВНИМАНИЕ: сейчас хардкод. Должны получать
        из Планировщика, используя интерфейс.
        """
        return [
            "BestCQI",
            "ProportionalFair",
            "RoundRobin",
            "FD_BCQI",
            "FD_FGS",
            "FD_PF",
            "BasicQosAware",
            "QosAware",
        ]

    def list_channel_models(self) -> List[str]:
        """Доступные модели канала."""
        return ["RMa", "UMa", "UMi", "RMa-SC"]

    def list_traffic_models(self) -> List[str]:
        """Доступные модели трафика."""
        return ["Poisson", "OnOff", "MMPP", "Periodic", "ConstBitrate"]

    def list_mobility_models(self) -> List[str]:
        """Доступные модели мобильности."""
        return [
            "RandomWalk",
            "RandomWaypoint",
            "RandomDirection",
            "GaussMarkov",
            "DiagonalWalk",
        ]
    
"""
API_MODULE.py — прослойка между ядром и интерфейсами (CLI, FastAPI).

Структура:
  Секция 0: Импорты
  Секция 1: Конфиги (вход)      — SimulationSpec + вложенные
  Секция 2: Результат (выход)   — SimulationResult
  Секция 3: ISimulationAPI (ABC)
  Секция 4: SimulationAPI (реализация)
  Секция 5: Парсинг файлов      — временный, до согласования формата

Контракт:
    CLI / FastAPI → ISimulationAPI → SimulationAPI
                                       ↓ asdict(spec)
                                    ISimulationManager.configure(**config)
                                       ↓
                                    ISimulationManager.start_simulation()
                                       ↓ (файлы созданы)
                                    _parse_stats_files(csv) → SimulationResult

Внимание: run() зависит от SimulationManager.configure() и
get_longterm_fairness(). Оба метода — неделя 9 (см. TODO).
Пока не реализованы — run() бросает NotImplementedError с понятным
сообщением. validate() и конфиги работают независимо.
"""

# ==============================================================================
# СЕКЦИЯ 0. ИМПОРТЫ
# ==============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import csv

from SIMULATION_MANAGER import ISimulationManager, SimulationManager


# ==============================================================================
# СЕКЦИЯ 1. КОНФИГИ
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
            raise ValueError(
                f"Количество UE должно быть > 0, получено {self.count}"
            )

        valid_classes = {"random", "pedestrian", "cyclist", "car"}
        if self.ue_class not in valid_classes:
            raise ValueError(
                f"Неизвестный ue_class '{self.ue_class}'. "
                f"Допустимые: {sorted(valid_classes)}"
            )

        if self.x_min >= self.x_max:
            raise ValueError(
                f"x_min должен быть < x_max, получено "
                f"{self.x_min} >= {self.x_max}"
            )
        if self.y_min >= self.y_max:
            raise ValueError(
                f"y_min должен быть < y_max, получено "
                f"{self.y_min} >= {self.y_max}"
            )


@dataclass(slots=True)
class SchedulerConfig:
    """Конфигурация планировщика. Валидация — неделя 9."""
    algorithm: str = "RoundRobin"
    max_dl_ue_tti: Optional[int] = None
    pcfich: int = 2
    max_dl_cce_allowance: Optional[int] = None
    window_size: int = 100
    enable_window: bool = True


@dataclass(slots=True)
class StatsConfig:
    """Конфигурация статистики. Валидация — неделя 9."""
    enabled: bool = True
    collect_interval: int = 1
    scheduler_level: str = "basic"
    amc_level: str = "basic"
    pdcch_level: str = "none"
    file_prefix: str = "sim_stats"


@dataclass(slots=True)
class SimulationSpec:
    """Полный конфиг симуляции."""
    duration: int = 5000
    update_interval: int = 1
    mobility_interval: int = 500
    channel_interval: int = 1
    seed: Optional[int] = None
    verbose: bool = False

    bs: BSConfig = field(default_factory=BSConfig)
    ues: UEConfig = field(default_factory=UEConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    stats: StatsConfig = field(default_factory=StatsConfig)

    def __post_init__(self):
        if self.duration <= 0:
            raise ValueError(
                f"Длительность симуляции должна быть > 0, "
                f"получено {self.duration}"
            )
        if self.update_interval <= 0:
            raise ValueError(
                f"Интервал обновления должен быть > 0, "
                f"получено {self.update_interval}"
            )
        if self.mobility_interval <= 0:
            raise ValueError(
                f"Интервал мобильности должен быть > 0, "
                f"получено {self.mobility_interval}"
            )
        if self.channel_interval <= 0:
            raise ValueError(
                f"Интервал канала должен быть > 0, "
                f"получено {self.channel_interval}"
            )


# ==============================================================================
# СЕКЦИЯ 2. РЕЗУЛЬТАТ
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
            "files": self.to_files(),
        }


# ==============================================================================
# СЕКЦИЯ 3. ISimulationAPI (ABC)
# ==============================================================================

class ISimulationAPI(ABC):
    """
    Публичный интерфейс API-модуля.

    CLI (Ника) и FastAPI работают через ISimulationAPI.
    Bootstrap — в CLI: SimulationAPI() — единственная точка,
    где интерфейс подменяется конкретным классом.
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
# СЕКЦИЯ 4. SimulationAPI
# ==============================================================================

class SimulationAPI(ISimulationAPI):
    """Реализация API. Тонкая прослойка: asdict → configure → start → parse."""

    def run(self, spec: SimulationSpec) -> SimulationResult:
        """
        Запустить симуляцию и вернуть результат.

        Зависит от SimulationManager.configure() и
        SimulationManager.get_longterm_fairness(). Пока не реализованы —
        бросает NotImplementedError с понятным сообщением.
        """
        config_dict = asdict(spec)

        sim: ISimulationManager = SimulationManager()

        if not hasattr(sim, "configure") or not callable(
            getattr(sim, "configure", None)
        ):
            raise NotImplementedError(
                "SimulationManager.configure(**config) ещё не реализован. "
                "Это ожидаемо: API-скелет готов, backend — неделя 9. "
                "См. TODO в отчёте."
            )

        sim.configure(**config_dict)
        sim.start_simulation()

        # После возврата start_simulation() файлы существуют (контракт).
        csv_path = f"{spec.stats.file_prefix}.csv"
        detailed_csv_path = f"{spec.stats.file_prefix}_detailed.csv"

        metrics = _parse_stats_files(csv_path, detailed_csv_path)

        jain = None
        if hasattr(sim, "get_longterm_fairness") and callable(
            getattr(sim, "get_longterm_fairness", None)
        ):
            jain = sim.get_longterm_fairness()

        return SimulationResult(
            duration_tti=spec.duration,
            algorithm=spec.scheduler.algorithm,
            num_ues=spec.ues.count,
            jain_fairness=jain,
            avg_cell_throughput_kbps=metrics["avg_throughput_kbps"],
            avg_spectral_efficiency=metrics["avg_se"],
            csv_path=csv_path,
            detailed_csv_path=detailed_csv_path,
        )

    def validate(self, spec: SimulationSpec) -> List[str]:
        """
        Проверить конфиг. Возвращает список ошибок (пустой = ок).

        На неделе 9 добавится валидация BSConfig, SchedulerConfig,
        StatsConfig через __post_init__ (или здесь).
        """
        errors: List[str] = []

        if spec.duration <= 0:
            errors.append("Длительность симуляции должна быть > 0")
        if spec.ues.count <= 0:
            errors.append("Количество UE должно быть > 0")

        valid_bandwidths = [1.4, 3, 5, 10, 15, 20]
        if spec.bs.bandwidth not in valid_bandwidths:
            errors.append(
                f"bs.bandwidth должен быть одним из {valid_bandwidths}, "
                f"получено {spec.bs.bandwidth}"
            )

        if spec.scheduler.algorithm not in self.list_algorithms():
            errors.append(
                f"scheduler.algorithm '{spec.scheduler.algorithm}' "
                f"не входит в {self.list_algorithms()}"
            )

        if spec.bs.ch_model_type not in self.list_channel_models():
            errors.append(
                f"bs.ch_model_type '{spec.bs.ch_model_type}' "
                f"не входит в {self.list_channel_models()}"
            )

        return errors

    def list_algorithms(self) -> List[str]:
        """
        Доступные алгоритмы планировщика.

        ВНИМАНИЕ: сейчас хардкод. Должно читаться из
        SchedulerInterface.create (реестр фабрики), не из
        available_algorithms() — там рассинхрон (см. отчёт 8, §7.1.1).
        """
        return [
            "BestCQI",
            "ProportionalFair",
            "RoundRobin",
            "FD_BCQI",
            "FD_FGS",
            "FD_PF",
            "BasicQosAware",
            "QosAware",
        ]

    def list_channel_models(self) -> List[str]:
        """Доступные модели канала."""
        return ["RMa", "UMa", "UMi", "RMa-SC"]

    def list_traffic_models(self) -> List[str]:
        """Доступные модели трафика."""
        return ["Poisson", "OnOff", "MMPP", "Periodic", "ConstBitrate"]

    def list_mobility_models(self) -> List[str]:
        """Доступные модели мобильности."""
        return [
            "RandomWalk",
            "RandomWaypoint",
            "RandomDirection",
            "GaussMarkov",
            "DiagonalWalk",
        ]


def _parse_stats_files(
    csv_path: str, detailed_csv_path: str
) -> Dict[str, float]:
    # TODO: заменить на реальный парсинг после согласования формата
    # с наставником (Stats Manager refactor, неделя 10+).
    return {
        "avg_throughput_kbps": 0.0,
        "avg_se": 0.0,
    }