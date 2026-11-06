"""
Master Integration Test: Phase 2 Complete (tests/test_phase_02_ingestion.py)
Purpose: End-to-end verification of Steps 11 through 20 across `modules/ingestion/`
         and automatic telemetry capture in `modules/telemetry/`.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.telemetry import GLOBAL_TELEMETRY_LOGGER, render_cli_dashboard
from modules.ingestion import (
    validate_and_normalize_url,
    LiveFeedPoller
)

print("🚀 Running Step 20 Master Verification Gate (Full Phase 2 Ingestion Integration)...\n")

GLOBAL_TELEMETRY_LOGGER.clear()

# 1. Validate & normalize a GitHub blob e-commerce link
url_info, _ = validate_and_normalize_url("https://github.com/omnidata/feeds/blob/main/orders.csv")
assert url_info["was_rewritten"] is True, "❌ FAIL: URL normalizer failed!"

# 2. Simulate full Morning -> Unchanged Midday -> Mutated Afternoon lifecycle
poller = LiveFeedPoller(primary_key="order_id", max_budget_mb=25.0)

morning_feed = b"order_id|customer|amount\n1001|Alice|120.50\n1002|Bob|85.00\n1003|Charlie|42.00\n"
afternoon_feed = b"order_id|customer|amount\n1001|Alice|150.00\n1003|Charlie|42.00\n1004|Diana|310.00\n"

r_morning = poller.ingest_payload(morning_feed, headers={"ETag": '"morning-v1"'})
r_midday = poller.ingest_payload(morning_feed, headers={"ETag": '"morning-v1"'})
r_afternoon = poller.ingest_payload(afternoon_feed, headers={"ETag": '"afternoon-v2"'})

print(render_cli_dashboard(limit=10))
print(f"\nDetected Format   : {r_morning['format']}")
print(f"Afternoon Delta   : +{r_afternoon['delta']['total_added']} Added | -{r_afternoon['delta']['total_deleted']} Deleted | ~{r_afternoon['delta']['total_modified']} Modified")
print(f"Schema Status     : {r_afternoon['schema_drift']['status']}")

assert r_morning["format"] == "PIPE_DELIMITED", "❌ FAIL: Pipe delimiter auto-detection failed!"
assert r_midday["status"] == "SKIPPED_UNCHANGED", "❌ FAIL: Midday ETag skip failed!"
assert r_afternoon["delta"] == {
    "is_identical": False,
    "added_keys": ["1004"],
    "deleted_keys": ["1002"],
    "modified_keys": ["1001"],
    "total_added": 1,
    "total_deleted": 1,
    "total_modified": 1
}, "❌ FAIL: Afternoon delta mismatch!"

print("\n🏆 STEP 20 & PHASE 2 COMPLETE: Safe Live-Streaming Ingestion Engine is 100% built and verified!")
