"""
Module: Stateful Live Feed Poller & Refresh Controller (modules/ingestion/live_poller.py)
Purpose: Orchestrates morning-to-afternoon dataset refreshes by combining ETag 
         preflight checks, bounded streaming, format sniffing, tabular parsing, 
         delta tracking, schema drift detection, and GC memory reclamation.
"""

import io
import os
import sys
from typing import Dict, Any, List, Optional, Mapping

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import GLOBAL_TELEMETRY_LOGGER, reclaim_memory
from modules.ingestion.http_preflight import evaluate_preflight_headers
from modules.ingestion.stream_reader import read_bounded_stream
from modules.ingestion.format_sniffer import sniff_stream_format
from modules.ingestion.tabular_parser import parse_tabular_stream
from modules.ingestion.snapshot_fingerprint import create_snapshot_fingerprint
from modules.ingestion.delta_tracker import compute_dataset_delta
from modules.ingestion.schema_validator import extract_schema, detect_schema_drift


class LiveFeedPoller:
    """
    Maintains only the latest active dataset snapshot in RAM and automatically 
    reclaims old snapshot memory via gc.collect(2) during live refreshes.
    """

    def __init__(
        self,
        primary_key: Optional[str] = None,
        max_budget_mb: float = 50.0
    ) -> None:
        self.primary_key = primary_key
        self.max_budget_mb = max_budget_mb
        self.last_etag: Optional[str] = None
        self.last_modified: Optional[str] = None
        self.active_rows: List[Dict[str, Any]] = []
        self.active_fingerprint: Optional[Dict[str, Any]] = None
        self.active_schema: Dict[str, str] = {}
        self.refresh_count: int = 0

    def ingest_payload(
        self,
        raw_bytes: bytes,
        headers: Optional[Mapping[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Processes a raw byte payload (morning initial load or afternoon update).
        """
        hdrs = dict(headers) if headers else {"Content-Length": str(len(raw_bytes))}

        # 1. O(1) Preflight & ETag Change Check
        preflight = evaluate_preflight_headers(
            headers=hdrs,
            previous_etag=self.last_etag,
            previous_modified=self.last_modified,
            max_budget_mb=self.max_budget_mb
        )

        if self.refresh_count > 0 and not preflight["has_changed"]:
            return {
                "status": "SKIPPED_UNCHANGED",
                "reason": preflight["change_reason"],
                "active_rows_count": len(self.active_rows),
                "refresh_count": self.refresh_count
            }

        # 2. Bounded Chunk Stream -> Format Sniff -> Tabular Parse
        text_buf, stream_meta = read_bounded_stream(
            io.BytesIO(raw_bytes),
            max_budget_mb=self.max_budget_mb
        )
        sniff_res, _ = sniff_stream_format(text_buf)
        new_rows, _ = parse_tabular_stream(
            text_buf,
            delimiter=sniff_res["delimiter"] or ",",
            has_header=sniff_res["has_header"]
        )
        text_buf.close()

        # 3. Fingerprint & Schema Extraction
        new_fp, _ = create_snapshot_fingerprint(new_rows, primary_key=self.primary_key)
        new_schema = extract_schema(new_rows)

        # 4. Compute Delta & Schema Drift if replacing an existing morning snapshot
        delta_report = None
        drift_report = None
        gc_report = None

        if self.active_fingerprint is not None:
            delta_report, _ = compute_dataset_delta(self.active_fingerprint, new_fp)
            drift_report, _ = detect_schema_drift(self.active_schema, new_schema)

            # Explicitly clear old references and trigger Step 6 GC sweep
            self.active_rows.clear()
            gc_report = reclaim_memory(generation=2, logger=GLOBAL_TELEMETRY_LOGGER)

        # 5. Promote new snapshot to active state
        self.active_rows = new_rows
        self.active_fingerprint = new_fp
        self.active_schema = new_schema
        self.last_etag = preflight["etag"]
        self.last_modified = preflight["last_modified"]
        self.refresh_count += 1

        return {
            "status": "INITIAL_LOADED" if self.refresh_count == 1 else "LIVE_REFRESHED",
            "format": sniff_res["format"],
            "active_rows_count": len(self.active_rows),
            "estimated_ram_mb": stream_meta["estimated_ram_mb"],
            "delta": delta_report,
            "schema_drift": drift_report,
            "gc_reclaimed": gc_report,
            "refresh_count": self.refresh_count
        }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 19 Verification Gate (Stateful Live Feed Poller)...\n")

    poller = LiveFeedPoller(primary_key="sku", max_budget_mb=20.0)

    # 1. Morning Snapshot Load
    morning_csv = b"sku,item,price\nA1,Keyboard,45.0\nA2,Monitor,210.0\n"
    res_1 = poller.ingest_payload(morning_csv, headers={"ETag": '"v1"'})
    print(f"[1/3] Morning Load      -> Status: {res_1['status']} | Rows: {res_1['active_rows_count']}")

    # 2. Midday Check with identical ETag (Zero-parse skip!)
    res_2 = poller.ingest_payload(morning_csv, headers={"ETag": '"v1"'})
    print(f"[2/3] Same ETag Poll    -> Status: {res_2['status']} ({res_2['reason']})")

    # 3. Afternoon Live Update (A1 price updated, A3 added)
    afternoon_csv = b"sku,item,price\nA1,Keyboard,39.0\nA2,Monitor,210.0\nA3,Webcam,65.0\n"
    res_3 = poller.ingest_payload(afternoon_csv, headers={"ETag": '"v2"'})
    print(f"[3/3] Afternoon Refresh -> Status: {res_3['status']} | Added: {res_3['delta']['total_added']} | Modified: {res_3['delta']['total_modified']} | GC Status: {res_3['gc_reclaimed']['status']}")

    assert res_1["status"] == "INITIAL_LOADED", "❌ FAIL: Initial load failed!"
    assert res_2["status"] == "SKIPPED_UNCHANGED", "❌ FAIL: ETag skip failed!"
    assert res_3["status"] == "LIVE_REFRESHED", "❌ FAIL: Afternoon refresh failed!"
    assert res_3["delta"]["total_added"] == 1 and res_3["delta"]["total_modified"] == 1, "❌ FAIL: Delta counts wrong!"

    print("\n✅ STEP 19 PASSED: Stateful Live Feed Poller & Refresh Controller is verified!")
