"""
Package: Unified Hardware Telemetry Facade (modules/telemetry/__init__.py)
Purpose: Connects memory_guard (Step 2), ram_limit_guard (Step 3), and 
         execution_logger (Step 4) into a single clean import interface.
         Provides @auto_log_telemetry so any pipeline function automatically 
         records its time and RAM complexity into the bounded ring buffer.
"""

from functools import wraps
from typing import Callable, Any, Tuple, Dict

from modules.telemetry.memory_guard import profile_execution
from modules.telemetry.ram_limit_guard import (
    enforce_ram_budget,
    MemoryBudgetExceededError
)
from modules.telemetry.execution_logger import TelemetryRingLogger


# -----------------------------------------------------------------------------
# BLOCK 1: GLOBAL SINGLETON RING-BUFFER LOGGER
# Why this block started: Creates one shared 50-slot ring buffer across the 
# entire application so the 'Deep Learn' tab can read telemetry from all 6 modules.
# Space Complexity: Strictly bounded O(1) — Capped at 50 entries maximum.
# -----------------------------------------------------------------------------
GLOBAL_TELEMETRY_LOGGER = TelemetryRingLogger(max_records=50)


# -----------------------------------------------------------------------------
# BLOCK 2: AUTO-LOGGING TELEMETRY DECORATOR
# Why this block started: Combines Step 2 (@profile_execution) and Step 4 
# (TelemetryRingLogger) so decorated functions automatically push their metrics 
# into GLOBAL_TELEMETRY_LOGGER without manual logging code.
# Time Complexity: O(1) overhead.
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# BLOCK 3: LOGGED RAM CIRCUIT BREAKER HELPER
# Why this block started: Wraps Step 3 (enforce_ram_budget) so that both 
# APPROVED and BLOCKED pre-execution payload checks are also recorded in the 
# live telemetry log for full visibility in the UI.
# -----------------------------------------------------------------------------
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


__all__ = [
    "profile_execution",
    "enforce_ram_budget",
    "MemoryBudgetExceededError",
    "TelemetryRingLogger",
    "GLOBAL_TELEMETRY_LOGGER",
    "auto_log_telemetry",
    "check_and_log_ram_budget"
]
