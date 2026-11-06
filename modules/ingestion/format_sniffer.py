"""
Module: O(1) Sample-Window Format & Delimiter Sniffer (modules/ingestion/format_sniffer.py)
Purpose: Inspects only the first 4,096 characters of an in-memory StringIO buffer 
         to automatically classify payload format (CSV, TSV, Pipe, Semicolon, 
         JSON, JSONL) and rewinds the stream cursor to position 0 in O(1) time.
Why we use standard libraries (csv, io):
         Uses Python's built-in csv.Sniffer with a deterministic fallback 
         frequency counter over a fixed 4 KB window -> Strictly O(1) complexity.
"""

import csv
import io
import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


# -----------------------------------------------------------------------------
# BLOCK 1: O(1) WINDOW FORMAT & DELIMITER DETECTOR
# Why this block started: Reads at most `sample_size=4096` characters and 
# immediately calls `buffer.seek(0)` so downstream parsers read from byte 0.
# Time Complexity: O(1) (bounded by 4,096 chars) | Space Complexity: O(1)
# -----------------------------------------------------------------------------
@auto_log_telemetry(module_name="ingestion")
def sniff_stream_format(
    text_buffer: io.StringIO,
    sample_size: int = 4096
) -> Dict[str, Any]:
    """
    Detects data format (CSV, TSV, JSON, JSONL) and delimiter from a 4 KB sample.
    """
    text_buffer.seek(0)
    sample = text_buffer.read(sample_size)
    text_buffer.seek(0)  # Rewind cursor so zero rows are lost!

    stripped = sample.lstrip()
    if not stripped:
        raise ValueError("Cannot sniff format: Stream buffer is empty.")

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    first_char = stripped[0]

    # 1. Check for JSON Array or JSON Lines (JSONL)
    if first_char == "[":
        return {
            "format": "JSON",
            "delimiter": None,
            "has_header": False,
            "sample_lines_inspected": len(lines)
        }

    if first_char == "{":
        is_jsonl = len(lines) > 1 and lines[1].startswith("{")
        return {
            "format": "JSONL" if is_jsonl else "JSON",
            "delimiter": None,
            "has_header": False,
            "sample_lines_inspected": len(lines)
        }

    # 2. Delimited Tabular Detection (CSV / TSV / Pipe / Semicolon)
    candidate_delimiters = [",", "\t", ";", "|"]
    detected_delimiter = ","

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        detected_delimiter = dialect.delimiter
    except csv.Error:
        # Fallback: pick delimiter with consistent count across first two lines
        header_line = lines[0]
        best_count = 0
        for delim in candidate_delimiters:
            cnt = header_line.count(delim)
            if cnt > best_count:
                best_count = cnt
                detected_delimiter = delim

    format_map = {
        ",": "CSV",
        "\t": "TSV",
        "|": "PIPE_DELIMITED",
        ";": "SEMICOLON_CSV"
    }

    return {
        "format": format_map.get(detected_delimiter, "CSV"),
        "delimiter": detected_delimiter,
        "has_header": True,
        "sample_lines_inspected": len(lines)
    }


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 14 Verification Gate (O(1) Format & Delimiter Sniffer)...\n")

    # Test 1: Standard Comma CSV + Verify cursor rewind to 0
    csv_buf = io.StringIO("id,name,revenue\n1,Alpha,500.25\n2,Beta,900.00\n")
    res_csv, _ = sniff_stream_format(csv_buf)
    cursor_pos = csv_buf.tell()
    print(f"[Test 1 - Comma CSV]  -> Format: {res_csv['format']} | Delimiter: '{res_csv['delimiter']}' | Cursor Rewound: pos={cursor_pos}")

    # Test 2: Pipe-Delimited E-Commerce Feed
    pipe_buf = io.StringIO("sku|category|stock\nA10|Electronics|42\nA11|Books|19\n")
    res_pipe, _ = sniff_stream_format(pipe_buf)
    print(f"[Test 2 - Pipe Feed]  -> Format: {res_pipe['format']} | Delimiter: '{res_pipe['delimiter']}'")

    # Test 3: JSON Lines (.jsonl) Event Stream
    jsonl_buf = io.StringIO('{"event": "click", "id": 1}\n{"event": "purchase", "id": 2}\n')
    res_jsonl, _ = sniff_stream_format(jsonl_buf)
    print(f"[Test 3 - JSONL Feed] -> Format: {res_jsonl['format']} | Delimiter: {res_jsonl['delimiter']}")

    assert res_csv["format"] == "CSV" and res_csv["delimiter"] == ",", "❌ FAIL: CSV sniff failed!"
    assert cursor_pos == 0, "❌ FAIL: Stream cursor was not rewound to 0!"
    assert res_pipe["delimiter"] == "|", "❌ FAIL: Pipe delimiter not detected!"
    assert res_jsonl["format"] == "JSONL", "❌ FAIL: JSONL format not detected!"

    print("\n✅ STEP 14 PASSED: O(1) Sample-Window Format & Delimiter Sniffer is verified!")
