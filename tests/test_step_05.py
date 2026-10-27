"""
Verification Gate: Step 05 — Unified Telemetry Facade (tests/test_step_05.py)
Purpose: Verifies that importing from `modules.telemetry` works cleanly and 
         that both `@auto_log_telemetry` and `check_and_log_ram_budget` 
         automatically populate `GLOBAL_TELEMETRY_LOGGER`.
"""

import os
import sys

# Ensure project root is on sys.path when running test directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.telemetry import (
    GLOBAL_TELEMETRY_LOGGER,
    auto_log_telemetry,
    check_and_log_ram_budget,
    MemoryBudgetExceededError
)

print("🔍 Running Step 05 Verification Gate (Unified Telemetry Facade)...\n")

# Reset global logger before test
GLOBAL_TELEMETRY_LOGGER.clear()

# 1. Test @auto_log_telemetry decorator
@auto_log_telemetry(module_name="eda_engine")
def compute_mock_statistics(n: int) -> int:
    data = [x * 2 for x in range(n)]
    return sum(data)

total, report = compute_mock_statistics(50_000)
print(f"[1/3] Auto-Logged Function Output : sum={total} | time={report['execution_time_ms']} ms")

# 2. Test Approved RAM Check auto-logging
safe_check = check_and_log_ram_budget(payload_bytes=2 * 1024 * 1024, module_name="ingestion")
print(f"[2/3] Auto-Logged Safe RAM Check  : {safe_check['status']} ({safe_check['estimated_ram_mb']} MB)")

# 3. Test Blocked RAM Check auto-logging
try:
    check_and_log_ram_budget(payload_bytes=20 * 1024 * 1024, module_name="ingestion", max_budget_mb=50.0)
except MemoryBudgetExceededError:
    print("[3/3] Auto-Logged Blocked Payload : Circuit Breaker Tripped & Logged Cleanly!")

# Verify all 3 events were automatically captured in GLOBAL_TELEMETRY_LOGGER
history = GLOBAL_TELEMETRY_LOGGER.get_history()
summary = GLOBAL_TELEMETRY_LOGGER.get_summary()

print(f"\nGlobal Logger Active Count : {summary['active_logs']}")
for idx, item in enumerate(history, 1):
    print(f"   Log #{idx} -> [{item['module']}] {item['function']} | {item['peak_memory_mb']} MB | {item['status']}")

assert summary["active_logs"] == 3, "❌ FAIL: Expected exactly 3 auto-logged events!"
assert history[0]["status"] == "BLOCKED", "❌ FAIL: Blocked circuit breaker event was not logged!"
assert history[1]["status"] == "APPROVED", "❌ FAIL: Approved circuit breaker event was not logged!"
assert history[2]["function"] == "compute_mock_statistics", "❌ FAIL: Decorated function was not logged!"

print("\n✅ STEP 05 PASSED: Unified Telemetry Facade is wired and verified!")
