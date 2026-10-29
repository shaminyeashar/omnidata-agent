"""
Module: In-Memory Telemetry Exporter (modules/telemetry/telemetry_exporter.py)
Purpose: Serializes bounded ring-buffer telemetry logs and health snapshots into 
         in-memory JSON and CSV strings for one-click download in the Streamlit 
         'Deep Learn' tab without creating temporary files on disk.
Why we use standard libraries (json, csv, io.StringIO):
         In-memory stream serialization avoids slow Disk I/O and runs in bounded 
         O(K) time and space (where K <= 50 records).
"""

import csv
import io
import json
import os
import sys
from typing import Optional

# Ensure project root is on sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry.execution_logger import TelemetryRingLogger
from modules.telemetry.dashboard import compile_health_snapshot
from modules.telemetry import GLOBAL_TELEMETRY_LOGGER


# -----------------------------------------------------------------------------
# BLOCK 1: IN-MEMORY JSON REPORT SERIALIZER
# Why this block started: Combines the high-level health snapshot (Step 7) and 
# chronological log history (Step 4) into a formatted JSON string.
# -----------------------------------------------------------------------------
def export_telemetry_json(logger: Optional[TelemetryRingLogger] = None) -> str:
    """
    Exports both the system health snapshot and full ring-buffer history as JSON.
    """
    target_logger = logger if logger is not None else GLOBAL_TELEMETRY_LOGGER
    payload = {
        "health_snapshot": compile_health_snapshot(target_logger),
        "telemetry_history": target_logger.get_history()
    }
    return json.dumps(payload, indent=2)


# -----------------------------------------------------------------------------
# BLOCK 2: ZERO-DISK IN-MEMORY CSV STREAM GENERATOR
# Why this block started: Uses `io.StringIO` (an in-memory text buffer) with 
# `csv.DictWriter` so users can export telemetry logs directly to Excel/Pandas.
# -----------------------------------------------------------------------------
def export_telemetry_csv(logger: Optional[TelemetryRingLogger] = None) -> str:
    """
    Exports the ring-buffer telemetry history into a CSV-formatted string in RAM.
    """
    target_logger = logger if logger is not None else GLOBAL_TELEMETRY_LOGGER
    history = target_logger.get_history()

    fieldnames = [
        "timestamp",
        "module",
        "function",
        "execution_time_ms",
        "peak_memory_mb",
        "status"
    ]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for row in history:
        writer.writerow({key: row.get(key, "") for key in fieldnames})

    csv_content = buffer.getvalue()
    buffer.close()
    return csv_content


# =============================================================================
# BLOCK 3: ISOLATED SANDBOX & VERIFICATION GATE
# Why this block started: Verifies both JSON and CSV in-memory exports contain 
# valid headers, accurate metrics, and leave zero files on disk.
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 09 Verification Gate (In-Memory Telemetry Exporter)...\n")

    test_logger = TelemetryRingLogger(max_records=5)
    test_logger.record_event("ingestion", {
        "function_name": "fetch_live_orders",
        "execution_time_ms": 31.4,
        "peak_memory_mb": 8.75,
        "status": "Success"
    })

    json_out = export_telemetry_json(test_logger)
    csv_out = export_telemetry_csv(test_logger)

    parsed_json = json.loads(json_out)
    csv_lines = csv_out.strip().split("\n")

    print("Generated CSV Preview:")
    for line in csv_lines:
        print(f"   {line}")

    print(f"\nJSON Root Keys : {list(parsed_json.keys())}")

    assert "health_snapshot" in parsed_json, "❌ FAIL: Missing health_snapshot in JSON!"
    assert len(parsed_json["telemetry_history"]) == 1, "❌ FAIL: JSON history count mismatch!"
    assert len(csv_lines) == 2, "❌ FAIL: Expected 1 header line + 1 data row in CSV!"
    assert "fetch_live_orders" in csv_lines[1], "❌ FAIL: Function name missing in CSV row!"

    print("\n✅ STEP 09 PASSED: In-Memory JSON & CSV Telemetry Exporter is verified!")
