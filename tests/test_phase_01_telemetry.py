"""
Master Integration Test: Phase 1 Complete (tests/test_phase_01_telemetry.py)
Purpose: End-to-end verification of Steps 01 through 10 across the entire 
         `modules/telemetry/` engine.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.telemetry import (
    GLOBAL_TELEMETRY_LOGGER,
    auto_log_telemetry,
    check_and_log_ram_budget,
    reclaim_memory,
    estimate_big_o,
    compile_health_snapshot,
    render_cli_dashboard,
    export_telemetry_json,
    export_telemetry_csv
)

print("🚀 Running Step 10 Master Verification Gate (Full Phase 1 Integration)...\n")

GLOBAL_TELEMETRY_LOGGER.clear()

# 1. Pre-execution RAM circuit breaker check (Step 3 + Step 5)
check_and_log_ram_budget(payload_bytes=3 * 1024 * 1024, module_name="ingestion")

# 2. Decorated workload execution at two sizes N1 & N2 (Step 2 + Step 4 + Step 5)
@auto_log_telemetry(module_name="eda_engine")
def linear_pass(n: int) -> int:
    arr = [i for i in range(n)]
    return sum(arr)

_, rep_n1 = linear_pass(20_000)
_, rep_n2 = linear_pass(200_000)

# 3. Empirical Big-O estimation on real RAM measurements (Step 8)
space_complexity = estimate_big_o(
    n1=20_000,
    cost_1=rep_n1["peak_memory_mb"],
    n2=200_000,
    cost_2=rep_n2["peak_memory_mb"],
    metric_type="Space"
)

# 4. Explicit Garbage Collection sweep logged to global buffer (Step 6)
reclaim_memory(generation=2, logger=GLOBAL_TELEMETRY_LOGGER)

# 5. Dashboard & Exporter verification (Step 7 + Step 9)
snapshot = compile_health_snapshot()
cli_view = render_cli_dashboard()
csv_report = export_telemetry_csv()
json_report = export_telemetry_json()

print(cli_view)
print(f"\nEmpirical Space Scaling Proof : {space_complexity['estimated_complexity']} (exponent={space_complexity['empirical_exponent']})")
print(f"CSV Export Lines Generated    : {len(csv_report.strip().splitlines())}")

assert snapshot["active_logs"] == 4, "❌ FAIL: Expected 4 integrated telemetry logs!"
assert snapshot["system_status"] == "HEALTHY", "❌ FAIL: System health should be HEALTHY!"
assert "O(N) Linear" in space_complexity["estimated_complexity"], "❌ FAIL: Expected O(N) Linear space proof!"
assert len(csv_report.strip().splitlines()) == 5, "❌ FAIL: Expected header + 4 rows in CSV!"

print("\n🏆 STEP 10 & PHASE 1 COMPLETE: Hardware Telemetry Engine is 100% built and verified!")
