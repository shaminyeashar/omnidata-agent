"""
Module: Bounded Ring-Buffer Telemetry Logger (modules/telemetry/execution_logger.py)
Purpose: Stores a chronological history of hardware telemetry reports (from Step 2 
         and Step 3) for the 'Deep Learn' UI tab without leaking RAM during 
         continuous live data refreshes.
Why we use standard libraries (collections.deque, datetime):
         deque(maxlen=K) provides an O(1) time and O(1) bounded-space ring buffer 
         written in C, automatically evicting oldest logs when capacity is reached.
"""

from collections import deque
from datetime import datetime
from typing import Dict, Any, List


class TelemetryRingLogger:
    """
    A memory-safe, bounded ring-buffer logger for pipeline execution metrics.

    Algorithmic Complexity:
    - record_event() : O(1) Time | O(1) Space (auto-evicts oldest item at maxlen)
    - get_history()  : O(K) Time | O(K) Space (where K <= maxlen, default 50)
    - get_summary()  : O(K) Time | O(1) Auxiliary Space
    """

    # -------------------------------------------------------------------------
    # BLOCK 1: INITIALIZE BOUNDED RING BUFFER
    # Why this block started: Allocates a fixed-capacity double-ended queue 
    # (deque) so even 100,000 live e-commerce refreshes never exceed maxlen.
    # -------------------------------------------------------------------------
    def __init__(self, max_records: int = 50) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be a positive integer.")
        self.max_records = max_records
        self._buffer: deque = deque(maxlen=max_records)

    # -------------------------------------------------------------------------
    # BLOCK 2: O(1) TELEMETRY EVENT INGESTION
    # Why this block started: Stamps each incoming telemetry dictionary from 
    # memory_guard or ram_limit_guard with an exact timestamp and pushes 
    # it into the circular buffer.
    # -------------------------------------------------------------------------
    def record_event(self, module_name: str, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module_name,
            "function": telemetry_data.get("function_name", "ram_circuit_breaker"),
            "execution_time_ms": float(telemetry_data.get("execution_time_ms", 0.0)),
            "peak_memory_mb": float(
                telemetry_data.get("peak_memory_mb", telemetry_data.get("estimated_ram_mb", 0.0))
            ),
            "status": telemetry_data.get("status", "UNKNOWN")
        }
        self._buffer.append(entry)
        return entry

    # -------------------------------------------------------------------------
    # BLOCK 3: CHRONOLOGICAL SNAPSHOT EXPORT (FOR 'DEEP LEARN' TAB)
    # Why this block started: Converts the internal deque into a newest-first 
    # Python list so Streamlit can render a live telemetry table cleanly.
    # -------------------------------------------------------------------------
    def get_history(self) -> List[Dict[str, Any]]:
        return list(reversed(self._buffer))

    # -------------------------------------------------------------------------
    # BLOCK 4: AGGREGATE COMPLEXITY SUMMARY
    # Why this block started: Computes total pipeline latency and highest RAM 
    # spike across active logs for high-level system health monitoring.
    # -------------------------------------------------------------------------
    def get_summary(self) -> Dict[str, Any]:
        if not self._buffer:
            return {
                "active_logs": 0,
                "max_capacity": self.max_records,
                "total_time_ms": 0.0,
                "max_peak_ram_mb": 0.0
            }

        total_time = round(sum(item["execution_time_ms"] for item in self._buffer), 3)
        max_ram = round(max(item["peak_memory_mb"] for item in self._buffer), 4)

        return {
            "active_logs": len(self._buffer),
            "max_capacity": self.max_records,
            "total_time_ms": total_time,
            "max_peak_ram_mb": max_ram
        }

    def clear(self) -> None:
        """Resets the ring buffer in O(1) time."""
        self._buffer.clear()


# =============================================================================
# BLOCK 5: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Pushes 8 simulated telemetry events into a buffer 
# capped at max_records=5 to mathematically prove old logs auto-evict without 
# growing beyond the memory cap.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 04 Verification Gate (Bounded Ring-Buffer Logger)...\n")

    # Initialize logger with a strict cap of 5 records for testing eviction
    logger = TelemetryRingLogger(max_records=5)

    # Simulate 8 consecutive pipeline refreshes (Events 1 through 8)
    for i in range(1, 9):
        fake_metric = {
            "function_name": f"fetch_live_batch_{i}",
            "execution_time_ms": 10.0 * i,
            "peak_memory_mb": round(0.5 * i, 2),
            "status": "Success"
        }
        logger.record_event(module_name="ingestion", telemetry_data=fake_metric)

    history = logger.get_history()
    summary = logger.get_summary()

    print(f"Buffer Capacity Cap : {summary['max_capacity']}")
    print(f"Active Logs Stored  : {summary['active_logs']} (After pushing 8 events)")
    print(f"Newest Log Recorded : {history[0]['function']} ({history[0]['peak_memory_mb']} MB)")
    print(f"Oldest Log Retained : {history[-1]['function']} (Events 1-3 auto-evicted!)")
    print(f"Telemetry Summary   : {summary}")

    # Rigorous Verification Assertions
    assert summary["active_logs"] == 5, "❌ FAIL: Ring buffer exceeded max_records cap!"
    assert history[0]["function"] == "fetch_live_batch_8", "❌ FAIL: Newest log mismatch!"
    assert history[-1]["function"] == "fetch_live_batch_4", "❌ FAIL: Oldest logs were not evicted!"
    assert summary["max_peak_ram_mb"] == 4.0, "❌ FAIL: Peak RAM summary calculation error!"

    print("\n✅ STEP 04 PASSED: Bounded O(1) Ring-Buffer Telemetry Logger is verified!")
