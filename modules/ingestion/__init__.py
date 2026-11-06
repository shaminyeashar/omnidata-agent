"""
Package: Complete Phase 2 Ingestion & Live-Streaming Facade (modules/ingestion/__init__.py)
Purpose: Exposes URL validation, HTTP preflight, bounded streaming, format sniffing,
         tabular parsing, SHA-256 fingerprinting, delta tracking, schema validation,
         and stateful live polling through a unified package interface.
"""

from modules.ingestion.url_validator import (
    UnsafeURLError,
    validate_and_normalize_url
)
from modules.ingestion.http_preflight import (
    evaluate_preflight_headers,
    inspect_remote_resource
)
from modules.ingestion.stream_reader import (
    read_bounded_stream,
    stream_url_to_buffer
)
from modules.ingestion.format_sniffer import sniff_stream_format
from modules.ingestion.tabular_parser import parse_tabular_stream
from modules.ingestion.snapshot_fingerprint import create_snapshot_fingerprint
from modules.ingestion.delta_tracker import compute_dataset_delta
from modules.ingestion.schema_validator import (
    extract_schema,
    detect_schema_drift
)
from modules.ingestion.live_poller import LiveFeedPoller

__all__ = [
    "UnsafeURLError",
    "validate_and_normalize_url",
    "evaluate_preflight_headers",
    "inspect_remote_resource",
    "read_bounded_stream",
    "stream_url_to_buffer",
    "sniff_stream_format",
    "parse_tabular_stream",
    "create_snapshot_fingerprint",
    "compute_dataset_delta",
    "extract_schema",
    "detect_schema_drift",
    "LiveFeedPoller"
]
