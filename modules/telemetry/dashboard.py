"""
Module: Telemetry Dashboard & Health Formatter (modules/telemetry/dashboard.py)
Purpose: Aggregates raw ring-buffer telemetry logs into structured UI health 
         snapshots and zero-dependency ASCII tables for terminal diagnostics 
         and the future Streamlit 'Deep Learn' tab.
Why we use standard libraries (sys, os, typing):
         Formatting <= 50 bounded records in pure Python runs in O(K) -> O(1) 
         bounded time and space without importing heavy table libraries.
"""

import os
import sys
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path when executed directly as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry.execution_logger import TelemetryRingLogger
from modules.telemetry import GLOBAL_TELEMETRY_LOGGER


# -----------------------------------------------------------------------------
# BLOCK 1: PIPELINE HEALTH & MODULE AGGREGATION ENGINE
# Why this block started: The UI needs top-level KPI cards (System Status, 
# Average Latency, Blocked Count, Per-Module RAM) rather than just raw logs.
# Time Complexity: O(K) where K <= max_records (50) -> Strictly bounded O(1).
# Space Complexity: O(M) where M is the number of active modules (<= 6).
# -----------------------------------------------------------------------------
def compile_health_snapshot(
    logger: Optional[TelemetryRingLogger] = None,
    ram_warning_mb: float = 35.0
) -> Dict[str, Any]:
    """
    Compiles a high-level health and complexity snapshot from the ring logger.
    """
    target_logger = logger if logger is not None else GLOBAL_TELEMETRY_LOGGER
    history = target_logger.get_history()
    summary = target_logger.get_summary()

    if not history:
        return {
            "system_status": "IDLE",
            "active_logs": 0,
            "max_capacity": summary["max_capacity"],
            "total_time_ms": 0.0,
            "avg_time_ms": 0.0,
            "max_peak_ram_mb": 0.0,
            "blocked_events": 0,
            "module_breakdown": {}
        }

    blocked_count = sum(1 for item in history if item["status"] == "BLOCKED")
    avg_time = round(summary["total_time_ms"] / summary["active_logs"], 3)

    # Determine overall system health badge
    if blocked_count > 0:
        system_status = "CRITICAL (GUARD TRIPPED)"
    elif summary["max_peak_ram_mb"] >= ram_warning_mb:
        system_status = "WARNING (HIGH RAM)"
    else:
        system_status = "HEALTHY"

    # Group telemetry metrics by module name (e.g., ingestion, eda_engine)
    module_breakdown: Dict[str, Dict[str, Any]] = {}
    for item in history:
        mod = item["module"]
        if mod not in module_breakdown:
            module_breakdown[mod] = {
                "calls": 0,
                "total_time_ms": 0.0,
                "max_ram_mb": 0.0
            }
        module_breakdown[mod]["calls"] += 1
        module_breakdown[mod]["total_time_ms"] = round(
            module_breakdown[mod]["total_time_ms"] + item["execution_time_ms"], 3
        )
        module_breakdown[mod]["max_ram_mb"] = max(
            module_breakdown[mod]["max_ram_mb"], item["peak_memory_mb"]
        )

    return {
        "system_status": system_status,
        "active_logs": summary["active_logs"],
        "max_capacity": summary["max_capacity"],
        "total_time_ms": summary["total_time_ms"],
        "avg_time_ms": avg_time,
        "max_peak_ram_mb": summary["max_peak_ram_mb"],
        "blocked_events": blocked_count,
        "module_breakdown": module_breakdown
    }


# -----------------------------------------------------------------------------
# BLOCK 2: ZERO-DEPENDENCY ASCII TABLE RENDERER
# Why this block started: Formats recent ring-buffer events into a clean table 
# for CLI debugging and code-block previews inside the 'Deep Learn' tab.
# -----------------------------------------------------------------------------
def render_cli_dashboard(
    logger: Optional[TelemetryRingLogger] = None,
    limit: int = 10
) -> str:
    """
    Renders a formatted ASCII telemetry report of the most recent N events.
    """
    target_logger = logger if logger is not None else GLOBAL_TELEMETRY_LOGGER
    snapshot = compile_health_snapshot(target_logger)
    history = target_logger.get_history()[: max(1, limit)]

    lines: List[str] = [
        "=" * 78,
        f"OMNIDATA-AGENT TELEMETRY DASHBOARD | STATUS: {snapshot['system_status']}",
        f"Logs: {snapshot['active_logs']}/{snapshot['max_capacity']} | "
        f"Total Time: {snapshot['total_time_ms']} ms | "
        f"Avg Time: {snapshot['avg_time_ms']} ms | "
        f"Peak RAM: {snapshot['max_peak_ram_mb']} MB",
        "=" * 78,
        f"{'TIMESTAMP':<19} | {'MODULE':<14} | {'FUNCTION':<22} | {'TIME(ms)':>8} | {'RAM(MB)':>7} | {'STATUS':<9}",
        "-" * 78
    ]

    if not history:
        lines.append("No telemetry events recorded yet.")
    else:
        for row in history:
            ts = row["timestamp"][:19]
            mod = row["module"][:14]
            fn = row["function"][:22]
            t_ms = f"{row['execution_time_ms']:.2f}"
            ram = f"{row['peak_memory_mb']:.2f}"
            st = row["status"][:9]
            lines.append(f"{ts:<19} | {mod:<14} | {fn:<22} | {t_ms:>8} | {ram:>7} | {st:<9}")

    lines.append("=" * 78)
    return "\n".join(lines)


# =============================================================================
# BLOCK 3: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Populates a test logger with healthy, GC, and blocked 
# telemetry events and verifies both KPI math and ASCII dashboard formatting.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 07 Verification Gate (Telemetry Dashboard Formatter)...\n")

    test_logger = TelemetryRingLogger(max_records=10)

    # 1. Simulate healthy ingestion & EDA events
    test_logger.record_event("ingestion", {
        "function_name": "stream_live_csv",
        "execution_time_ms": 42.5,
        "peak_memory_mb": 12.4,
        "status": "Success"
    })
    test_logger.record_event("eda_engine", {
        "function_name": "compute_column_stats",
        "execution_time_ms": 18.0,
        "peak_memory_mb": 6.2,
        "status": "Success"
    })

    # Verify HEALTHY state before any circuit breaker trip
    healthy_snap = compile_health_snapshot(test_logger)
    assert healthy_snap["system_status"] == "HEALTHY", "❌ FAIL: Expected HEALTHY status!"
    assert healthy_snap["avg_time_ms"] == 30.25, "❌ FAIL: Average time math error!"

    # 2. Simulate a blocked oversized payload
    test_logger.record_event("ingestion", {
        "function_name": "enforce_ram_budget",
        "execution_time_ms": 0.0,
        "peak_memory_mb": 96.0,
        "status": "BLOCKED"
    })

    critical_snap = compile_health_snapshot(test_logger)
    dashboard_text = render_cli_dashboard(test_logger, limit=5)

    print(dashboard_text)
    print(f"\nModule Breakdown : {critical_snap['module_breakdown']}")

    # Rigorous Verification Assertions
    assert critical_snap["system_status"] == "CRITICAL (GUARD TRIPPED)", "❌ FAIL: Status did not trip!"
    assert critical_snap["blocked_events"] == 1, "❌ FAIL: Blocked count mismatch!"
    assert critical_snap["module_breakdown"]["ingestion"]["calls"] == 2, "❌ FAIL: Module call count error!"
    assert "OMNIDATA-AGENT TELEMETRY DASHBOARD" in dashboard_text, "❌ FAIL: ASCII header missing!"

    print("\n✅ STEP 07 PASSED: Telemetry Dashboard & Summary Formatter is verified!")
