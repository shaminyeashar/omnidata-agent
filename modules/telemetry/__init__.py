"""
Package: Complete Phase 1 Hardware Telemetry Facade (modules/telemetry/__init__.py)
Purpose: Exposes all Phase 1 telemetry sensors, circuit breakers, ring loggers,
         GC reclaimers, Big-O estimators, dashboards, and exporters through a 
         single unified package interface (`from modules.telemetry import ...`).
"""

from functools import wraps
from typing import Callable, Any, Tuple, Dict

from modules.telemetry.memory_guard import profile_execution
from modules.telemetry.ram_limit_guard import (
    enforce_ram_budget,
    MemoryBudgetExceededError
)
from modules.telemetry.execution_logger import TelemetryRingLogger
from modules.telemetry.gc_reclaimer import reclaim_memory
from modules.telemetry.complexity_estimator import estimate_big_o

# Shared 50-slot bounded O(1) singleton ring buffer across all modules
GLOBAL_TELEMETRY_LOGGER = TelemetryRingLogger(max_records=50)


def auto_log_telemetry(module_name: str = "pipeline") -> Callable:
    """
    Decorator factory that profiles a function's execution time and peak RAM,
    automatically logs the report into GLOBAL_TELEMETRY_LOGGER, and returns 
    (result, telemetry_report).
    """
    def decorator(func: Callable) -> Callable:
        profiled_func = profile_execution(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Tuple[Any, Dict[str, Any]]:
            result, telemetry_report = profiled_func(*args, **kwargs)
            GLOBAL_TELEMETRY_LOGGER.record_event(
                module_name=module_name,
                telemetry_data=telemetry_report
            )
            return result, telemetry_report

        return wrapper
    return decorator


def check_and_log_ram_budget(
    payload_bytes: int,
    module_name: str = "ingestion",
    max_budget_mb: float = 50.0,
    expansion_factor: float = 4.0
) -> Dict[str, Any]:
    """
    Runs the O(1) RAM circuit breaker and logs the result into the ring buffer.
    """
    try:
        report = enforce_ram_budget(
            payload_bytes=payload_bytes,
            max_budget_mb=max_budget_mb,
            expansion_factor=expansion_factor
        )
        GLOBAL_TELEMETRY_LOGGER.record_event(
            module_name=module_name,
            telemetry_data=report
        )
        return report
    except MemoryBudgetExceededError as err:
        blocked_report = {
            "function_name": "enforce_ram_budget",
            "execution_time_ms": 0.0,
            "estimated_ram_mb": round((payload_bytes / (1024 * 1024)) * expansion_factor, 4),
            "status": "BLOCKED"
        }
        GLOBAL_TELEMETRY_LOGGER.record_event(
            module_name=module_name,
            telemetry_data=blocked_report
        )
        raise err


# Import dashboard and exporter helpers after GLOBAL_TELEMETRY_LOGGER is defined
from modules.telemetry.dashboard import (
    compile_health_snapshot,
    render_cli_dashboard
)
from modules.telemetry.telemetry_exporter import (
    export_telemetry_json,
    export_telemetry_csv
)

__all__ = [
    "profile_execution",
    "enforce_ram_budget",
    "MemoryBudgetExceededError",
    "TelemetryRingLogger",
    "GLOBAL_TELEMETRY_LOGGER",
    "auto_log_telemetry",
    "check_and_log_ram_budget",
    "reclaim_memory",
    "estimate_big_o",
    "compile_health_snapshot",
    "render_cli_dashboard",
    "export_telemetry_json",
    "export_telemetry_csv"
]
