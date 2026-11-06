"""
Module: Pure-Python Type Inference & Tabular Parser (modules/ingestion/tabular_parser.py)
Purpose: Converts an in-memory text buffer into a structured list of dictionaries,
         automatically inferring numeric types without relying on Pandas overhead.
Why we use standard libraries (csv, io):
         Parses streams in strict O(N) time with minimal memory allocation overhead.
"""

import csv
import io
import os
import sys
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from modules.telemetry import auto_log_telemetry


def _infer_value(val: str) -> Any:
    """Attempts to cast a string to int or float in O(1) time."""
    v = val.strip()
    if not v:
        return None
    
    # Fast-path for integers
    if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
        return int(v)
    
    # Fast-path for floats
    try:
        return float(v)
    except ValueError:
        return v


@auto_log_telemetry(module_name="ingestion")
def parse_tabular_stream(
    text_buffer: io.StringIO, 
    delimiter: str = ",", 
    has_header: bool = True
) -> List[Dict[str, Any]]:
    """
    Parses a bounded text stream into a structured list of typed dictionaries.
    """
    text_buffer.seek(0)
    reader = csv.reader(text_buffer, delimiter=delimiter)
    
    parsed_data = []
    headers = []
    
    for i, row in enumerate(reader):
        # Handle empty lines
        if not row:
            continue
            
        # Extract headers on first line
        if i == 0 and has_header:
            headers = [h.strip() for h in row]
            continue
            
        # Auto-generate headers if missing
        if not has_header and not headers:
            headers = [f"col_{j}" for j in range(len(row))]
            
        # Map row values to headers and infer types
        row_dict = {}
        for j, val in enumerate(row):
            header_name = headers[j] if j < len(headers) else f"col_{j}"
            row_dict[header_name] = _infer_value(val)
            
        parsed_data.append(row_dict)
        
    return parsed_data


# =============================================================================
# BLOCK 2: ISOLATED SANDBOX & VERIFICATION GATE
# =============================================================================
if __name__ == "__main__":
    print("🔍 Running Step 15 Verification Gate (Tabular Parser)...\n")

    csv_data = "id,product,price,in_stock\n101,Laptop,850.50,42\n102,Mouse,25.00,0\n"
    buffer = io.StringIO(csv_data)
    
    parsed, rep = parse_tabular_stream(buffer, delimiter=",", has_header=True)
    
    print(f"Parsed {len(parsed)} rows in {rep['execution_time_ms']} ms.")
    print(f"Row 1: {parsed[0]}")
    
    assert len(parsed) == 2, "❌ FAIL: Incorrect row count parsed!"
    assert isinstance(parsed[0]["id"], int), "❌ FAIL: Integer type inference failed!"
    assert isinstance(parsed[0]["price"], float), "❌ FAIL: Float type inference failed!"
    assert parsed[1]["in_stock"] == 0, "❌ FAIL: Missing or incorrect zero value!"

    print("\n✅ STEP 15 PASSED: Pure-Python Tabular Parser is verified!")
