"""
Module: Hardware Telemetry & Complexity Guard (modules/telemetry/memory_guard.py)
Purpose: Measures exact execution time (Time Complexity) and peak RAM allocation 
         (Space Complexity) of any function in our pipeline.
Why we use standard libraries (	ime, 	racemalloc, unctools):
         Zero external RAM overhead. Works natively in Python without pip packages.
"""

import time
import tracemalloc
from functools import wraps
from typing import Callable, Any, Tuple, Dict


def profile_execution(func: Callable) -> Callable:
    """
    A Python Decorator that wraps any function to measure its exact runtime 
    and memory footprint.

    Algorithmic Overhead of this Profiler:
    - Time Complexity: O(1) — Captures start/stop timestamps in constant time.
    - Space Complexity: O(1) — Stores a single dictionary of 4 scalar metrics.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Tuple[Any, Dict[str, Any]]:
        # ---------------------------------------------------------------------
        # BLOCK 1: INITIALIZE HARDWARE SENSORS
        # Why this block started: Starts tracing Python memory blocks and 
        # records the high-resolution CPU clock before the function runs.
        # ---------------------------------------------------------------------
        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            # -----------------------------------------------------------------
            # BLOCK 2: EXECUTE TARGET PIPELINE FUNCTION
            # Why this block started: Runs the actual data function and 
            # captures its output while sensors are active.
            # -----------------------------------------------------------------
            result = func(*args, **kwargs)
        finally:
            # -----------------------------------------------------------------
            # BLOCK 3: CAPTURE PEAK MEMORY & ELAPSED TIME
            # Why this block started: 'finally' guarantees that even if a 
            # function crashes, we stop tracemalloc so we never leak memory.
            # -----------------------------------------------------------------
            current_bytes, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            end_time = time.perf_counter()

        # ---------------------------------------------------------------------
        # BLOCK 4: COMPUTE TELEMETRY REPORT (FOR 'DEEP LEARN' TAB)
        # Why this block started: Converts raw bytes to KB/MB and seconds to 
        # milliseconds (ms) for human-readable engineering reports.
        # ---------------------------------------------------------------------
        elapsed_ms = round((end_time - start_time) * 1000, 3)
        peak_kb = round(peak_bytes / 1024, 3)
        peak_mb = round(peak_bytes / (1024 * 1024), 4)

        telemetry_report = {
            "function_name": func.__name__,
            "execution_time_ms": elapsed_ms,
            "peak_memory_kb": peak_kb,
            "peak_memory_mb": peak_mb,
            "status": "Success"
        }

        return result, telemetry_report

    return wrapper


# =============================================================================
# BLOCK 5: ISOLATED SANDBOX TEST
# Why this block started: Tests the profiler on an O(N) list allocation so we 
# can verify it accurately tracks time and RAM before moving to Step 3.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 02 Verification Gate (Telemetry Profiler)...\n")

    @profile_execution
    def simulate_data_allocation(n_elements: int) -> int:
        """Simulates O(N) time and O(N) space by allocating N integers."""
        dummy_list = [i for i in range(n_elements)]
        return len(dummy_list)

    # Test with 100,000 integers
    count, metrics = simulate_data_allocation(100_000)

    print(f"Processed Elements : {count}")
    print(f"Telemetry Report   : {metrics}")

    # Rigorous Verification Assertions
    assert count == 100_000, "❌ FAIL: Function output corrupted!"
    assert metrics["execution_time_ms"] > 0, "❌ FAIL: Timer did not record!"
    assert metrics["peak_memory_kb"] > 100, "❌ FAIL: Memory tracker did not record!"

    print("\n✅ STEP 02 PASSED: Time & Space Complexity Guard is active and verified!")
