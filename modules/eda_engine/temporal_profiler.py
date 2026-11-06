"""
Module: ISO-8601 Temporal Detector & Span Profiler (modules/eda_engine/temporal_profiler.py)
"""

from datetime import datetime
import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry

SUPPORTED_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y"
)


def _try_parse_date(val: Any) -> Optional[datetime]:
    if not isinstance(val, str):
        return None
    s = val.strip()
    if len(s) < 8 or len(s) > 32:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


@auto_log_telemetry(module_name="eda_engine")
def profile_temporal_columns(parsed_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not parsed_data:
        return {}
    columns = list(parsed_data[0].keys())
    temporal_stats: Dict[str, Dict[str, Any]] = {}

    for col in columns:
        valid_dates = 0
        non_empty = 0
        min_dt: Optional[datetime] = None
        max_dt: Optional[datetime] = None
        unique_timestamps = set()

        for row in parsed_data:
            val = row.get(col)
            if val is None or val == "":
                continue
            non_empty += 1
            dt = _try_parse_date(val)
            if dt is not None:
                valid_dates += 1
                unique_timestamps.add(dt)
                if min_dt is None or dt < min_dt:
                    min_dt = dt
                if max_dt is None or dt > max_dt:
                    max_dt = dt

        if non_empty == 0 or (valid_dates / non_empty) < 0.8 or min_dt is None or max_dt is None:
            continue

        span_days = round((max_dt - min_dt).total_seconds() / 86400.0, 2)
        distinct_count = len(unique_timestamps)
        avg_step_days = span_days / max(1, distinct_count - 1) if distinct_count > 1 else 0.0

        if avg_step_days == 0.0:
            granularity = "SINGLE_TIMESTAMP"
        elif avg_step_days < 0.9:
            granularity = "INTRADAY_HOURLY"
        elif avg_step_days <= 2.0:
            granularity = "DAILY"
        elif avg_step_days <= 10.0:
            granularity = "WEEKLY"
        else:
            granularity = "MONTHLY_OR_SPARSE"

        temporal_stats[col] = {
            "valid_date_count": valid_dates,
            "distinct_timestamps": distinct_count,
            "min_date": min_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "max_date": max_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "span_days": span_days,
            "inferred_granularity": granularity
        }
    return temporal_stats


if __name__ == "__main__":
    rows = [
        {"order_id": 1, "order_date": "2026-10-01", "category": "Tech"},
        {"order_id": 2, "order_date": "2026-10-02", "category": "Tech"},
        {"order_id": 3, "order_date": "2026-10-03", "category": "Books"},
        {"order_id": 4, "order_date": "2026-10-04", "category": "Home"},
    ]
    res, _ = profile_temporal_columns(rows)
    assert "category" not in res and res["order_date"]["span_days"] == 3.0
    print("✅ STEP 27 PASSED: Temporal Date/Time Profiler verified!")
