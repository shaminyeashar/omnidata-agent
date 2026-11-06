"""
Module: Bounded Chunked In-Memory Stream Reader (modules/ingestion/stream_reader.py)
Purpose: Streams raw byte chunks (default 64 KB) into an in-memory io.StringIO 
         buffer while enforcing a strict mid-stream byte ceiling so chunked HTTP 
         streams without Content-Length headers can never overflow 8 GB RAM.
Why we use standard libraries (io, urllib.request):
         Streams directly from network sockets into RAM buffers with zero temp 
         files on disk and O(1) chunk verification overhead.
"""

import io
import os
import sys
import urllib.request
from typing import Dict, Any, BinaryIO, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import (
    auto_log_telemetry,
    check_and_log_ram_budget,
    MemoryBudgetExceededError
)
from modules.ingestion.url_validator import validate_and_normalize_url


# -----------------------------------------------------------------------------
# BLOCK 1: MID-STREAM BOUNDED CHUNK READER
# Why this block started: Reads any binary stream (HTTP socket or BytesIO) in 
# small 64 KB blocks, checking the cumulative RAM expansion after every chunk.
# Time Complexity: O(N) in payload bytes | Auxiliary Chunk Space: O(1) (64 KB)
# -----------------------------------------------------------------------------
def read_bounded_stream(
    byte_stream: BinaryIO,
    max_budget_mb: float = 50.0,
    expansion_factor: float = 4.0,
    chunk_size_bytes: int = 65536,
    encoding: str = "utf-8"
) -> Tuple[io.StringIO, Dict[str, Any]]:
    """
    Reads a binary stream in bounded chunks into a decoded io.StringIO buffer.
    Trips MemoryBudgetExceededError immediately if cumulative bytes exceed budget.
    """
    max_raw_bytes = int((max_budget_mb * 1024 * 1024) / expansion_factor)
    total_bytes_read = 0
    chunks_read = 0
    raw_chunks = bytearray()

    while True:
        chunk = byte_stream.read(chunk_size_bytes)
        if not chunk:
            break

        total_bytes_read += len(chunk)
        chunks_read += 1

        # Mid-stream circuit breaker check
        if total_bytes_read > max_raw_bytes:
            check_and_log_ram_budget(
                payload_bytes=total_bytes_read,
                module_name="ingestion",
                max_budget_mb=max_budget_mb,
                expansion_factor=expansion_factor
            )

        raw_chunks.extend(chunk)

    # Log approved final payload size into telemetry ring buffer
    budget_report = check_and_log_ram_budget(
        payload_bytes=max(1, total_bytes_read),
        module_name="ingestion",
        max_budget_mb=max_budget_mb,
        expansion_factor=expansion_factor
    )

    decoded_text = raw_chunks.decode(encoding, errors="replace")
    raw_chunks.clear()  # Immediately free intermediate bytearray

    text_buffer = io.StringIO(decoded_text)
    metadata = {
        "total_bytes_read": total_bytes_read,
        "chunks_read": chunks_read,
        "estimated_ram_mb": budget_report["estimated_ram_mb"],
        "encoding": encoding,
        "status": "STREAM_COMPLETE"
    }
    return text_buffer, metadata


# -----------------------------------------------------------------------------
# BLOCK 2: NETWORK URL CHUNKED STREAM FETCHER
# Why this block started: Connects validated URLs to `read_bounded_stream`.
# -----------------------------------------------------------------------------
@auto_log_telemetry(module_name="ingestion")
def stream_url_to_buffer(
    url: str,
    max_budget_mb: float = 50.0,
    expansion_factor: float = 4.0,
    timeout_sec: float = 15.0
) -> Tuple[io.StringIO, Dict[str, Any]]:
    """
    Streams a validated remote URL into an in-memory StringIO buffer safely.
    """
    val_result, _ = validate_and_normalize_url(url)
    target_url = val_result["normalized_url"]

    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "OmniData-Agent/1.0 (Bounded-Stream-Reader)"}
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as response:
        buffer, meta = read_bounded_stream(
            byte_stream=response,
            max_budget_mb=max_budget_mb,
            expansion_factor=expansion_factor
        )
    meta["normalized_url"] = target_url
    return buffer, meta


# =============================================================================
# BLOCK 3: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 13 Verification Gate (Bounded Chunked Stream Reader)...\n")

    # Test 1: Stream a safe 120 KB CSV payload in 32 KB chunks
    sample_csv = ("order_id,product,price\n101,Laptop,850.50\n" * 3500).encode("utf-8")
    safe_stream = io.BytesIO(sample_csv)

    text_buf, meta = read_bounded_stream(safe_stream, max_budget_mb=10.0, chunk_size_bytes=32768)
    first_line = text_buf.readline().strip()
    print(f"[Test 1 - Safe Chunked Stream] -> Read {meta['total_bytes_read']} bytes in {meta['chunks_read']} chunks | Header: '{first_line}'")

    # Test 2: Simulate a rogue stream exceeding a 1.0 MB RAM budget mid-stream
    rogue_payload = b"x" * (400 * 1024)  # 400 KB raw * 4.0x expansion = 1.6 MB (> 1.0 MB cap)
    rogue_stream = io.BytesIO(rogue_payload)

    mid_stream_aborted = False
    try:
        read_bounded_stream(rogue_stream, max_budget_mb=1.0, expansion_factor=4.0, chunk_size_bytes=65536)
    except MemoryBudgetExceededError:
        mid_stream_aborted = True
        print("[Test 2 - Mid-Stream Breaker]  -> Rogue stream aborted mid-flight before RAM overflow!")

    assert meta["chunks_read"] >= 3, "❌ FAIL: Expected multi-chunk reading!"
    assert first_line == "order_id,product,price", "❌ FAIL: Stream content corrupted!"
    assert mid_stream_aborted is True, "❌ FAIL: Mid-stream circuit breaker did not trip!"

    print("\n✅ STEP 13 PASSED: Bounded Chunked In-Memory Stream Reader is verified!")
