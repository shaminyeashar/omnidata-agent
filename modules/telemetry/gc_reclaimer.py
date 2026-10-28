"""
Module: Garbage Collection & Memory Reclaimer (modules/telemetry/gc_reclaimer.py)
Purpose: Forcefully sweeps cyclic references and orphaned Python objects between 
         live data refreshes so old morning datasets never linger in 8 GB RAM 
         when afternoon updates arrive.
Why we use standard libraries (gc, time, tracemalloc):
         Hooks directly into CPython's generational garbage collector (Generations 0, 1, 2)
         with zero external dependency overhead.
"""

import gc
import os
import sys
import time
import tracemalloc
from typing import Dict, Any, Optional

# Ensure project root is on sys.path when executed directly as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry.execution_logger import TelemetryRingLogger


# -----------------------------------------------------------------------------
# BLOCK 1: EXPLICIT GENERATIONAL GARBAGE SWEEP
# Why this block started: Python's automatic GC only triggers based on object 
# allocation thresholds, which can leave large cyclic structures (like complex 
# graphs or chained DataFrame views) sitting in RAM. gc.collect() forces an 
# immediate full sweep across all 3 object generations (0, 1, and 2).
# -----------------------------------------------------------------------------
def reclaim_memory(
    generation: int = 2,
    logger: Optional[TelemetryRingLogger] = None
) -> Dict[str, Any]:
    """
    Executes an explicit garbage collection sweep and measures reclaimed memory.
    """
    if generation not in (0, 1, 2):
        raise ValueError("GC generation must be 0, 1, or 2.")

    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()

    start_time = time.perf_counter()
    bytes_before, _ = tracemalloc.get_traced_memory()

    # Force CPython generational garbage collection sweep
    unreachable_objects_freed = gc.collect(generation)

    bytes_after, _ = tracemalloc.get_traced_memory()
    end_time = time.perf_counter()

    if not was_tracing:
        tracemalloc.stop()

    reclaimed_bytes = max(0, bytes_before - bytes_after)
    reclaimed_kb = round(reclaimed_bytes / 1024, 3)
    reclaimed_mb = round(reclaimed_bytes / (1024 * 1024), 4)
    elapsed_ms = round((end_time - start_time) * 1000, 3)

    report = {
        "function_name": f"reclaim_memory_gen{generation}",
        "execution_time_ms": elapsed_ms,
        "objects_freed": unreachable_objects_freed,
        "reclaimed_kb": reclaimed_kb,
        "peak_memory_mb": reclaimed_mb,
        "status": "RECLAIMED"
    }

    if logger is not None:
        logger.record_event(module_name="telemetry_gc", telemetry_data=report)

    return report


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Creates 1,000 cyclic object pairs (Node A points to 
# Node B, and Node B points back to Node A) that standard reference counting 
# cannot free on its own, then proves reclaim_memory() sweeps them cleanly.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 06 Verification Gate (GC Memory Reclaimer)...\n")

    class CyclicNode:
        """Helper class to simulate cyclic references in memory."""
        def __init__(self, payload_size: int = 100) -> None:
            self.partner = None
            self.data = [0] * payload_size

    gc.disable()
    try:
        for _ in range(1000):
            node_a = CyclicNode(200)
            node_b = CyclicNode(200)
            node_a.partner = node_b
            node_b.partner = node_a

        del node_a, node_b

        test_logger = TelemetryRingLogger(max_records=10)
        sweep_report = reclaim_memory(generation=2, logger=test_logger)
    finally:
        gc.enable()

    print(f"Cyclic Objects Freed : {sweep_report['objects_freed']}")
    print(f"Sweep Duration       : {sweep_report['execution_time_ms']} ms")
    print(f"GC Telemetry Report  : {sweep_report}")
    print(f"Logged in RingBuffer : {len(test_logger.get_history())} event(s)")

    assert sweep_report["objects_freed"] >= 2000, "❌ FAIL: Cyclic objects were not freed!"
    assert sweep_report["status"] == "RECLAIMED", "❌ FAIL: Status mismatch!"
    assert len(test_logger.get_history()) == 1, "❌ FAIL: Event not logged to ring buffer!"

    print("\n✅ STEP 06 PASSED: Garbage Collection & Memory Reclaimer is verified!")
