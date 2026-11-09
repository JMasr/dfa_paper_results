#!/usr/bin/env python3
"""Verify original stage manifests plus metadata and reference integrity."""
import sys
from reproduce import verify_inputs

if __name__ == "__main__":
    try:
        inputs = verify_inputs()
        print(f"PASS: {len(inputs)} input hashes and both stage manifests verified")
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
