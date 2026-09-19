#!/usr/bin/env python3
"""Validate a staged public www.tevcat.org snapshot before normalization."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.staging / "manifest.json").read_text(encoding="utf-8"))
    public = json.loads((args.staging / "public-sources.json").read_text(encoding="utf-8"))
    rows = public.get("sources")
    if manifest.get("source_url") != "https://www.tevcat.org/" or not manifest.get("complete"):
        raise ValueError("staging manifest is not a complete www TeVCat snapshot")
    if not isinstance(rows, list) or len(rows) != manifest.get("source_count"):
        raise ValueError("source count mismatch")
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or any(not isinstance(identifier, int) or identifier <= 0 for identifier in ids):
        raise ValueError("invalid public source ID")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate public source ID")
    serialized = json.dumps(public, ensure_ascii=False).lower()
    if "private_notes" in serialized or '"owner"' in serialized:
        raise ValueError("private field survived staging")
    if hashlib.sha256(encoded(public)).hexdigest() != manifest.get("public_payload_sha256"):
        raise ValueError("public payload hash mismatch")
    print(json.dumps({"valid": True, "source_count": len(rows), "groups": manifest.get("catalogue_group_counts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
