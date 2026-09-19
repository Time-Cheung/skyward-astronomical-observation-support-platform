#!/usr/bin/env python3
"""Acquire the public TeVCat page snapshot without retaining private records."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import ssl
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import certifi

BASE_URL = "https://www.tevcat.org/"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = "Skyward-CatalogueSnapshot/1.1 (public astronomy data)"
PRIVATE_KEYS = {"private_notes", "owner"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".partial")
    pending.write_bytes(encoded(value) + b"\n")
    pending.replace(path)


def fetch() -> bytes:
    context = ssl.create_default_context(cafile=certifi.where())
    request = Request(BASE_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=30, context=context) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("TeVCat page exceeds bounded response size")
    return payload


def extract_public_records(payload: bytes) -> tuple[dict, list[dict]]:
    text = payload.decode("utf-8")
    match = re.search(r'var dat\s*=\s*"([A-Za-z0-9+/=]+)"', text)
    if not match:
        raise ValueError("public TeVCat dat payload not found")
    decoded = base64.b64decode(match.group(1))
    document = json.loads(decoded)
    if not isinstance(document, dict) or not isinstance(document.get("sources"), list):
        raise ValueError("public TeVCat dat payload has no sources array")
    catalogs = document.get("catalogs")
    if not isinstance(catalogs, dict):
        raise ValueError("public TeVCat dat payload has no catalog dictionary")
    allowed = []
    seen = set()
    for row in document["sources"]:
        if not isinstance(row, dict) or row.get("public") != 1:
            continue
        identifier = row.get("id")
        if not isinstance(identifier, int) or identifier <= 0 or identifier in seen:
            raise ValueError("missing or duplicate public TeVCat source ID")
        if not isinstance(row.get("canonical_name"), str) or not row["canonical_name"].strip():
            raise ValueError(f"missing canonical_name for {identifier}")
        if row.get("catalog_id") not in {int(key) for key in catalogs if str(key).isdigit()}:
            raise ValueError(f"unknown catalogue group for {identifier}")
        seen.add(identifier)
        allowed.append({key: value for key, value in row.items() if key not in PRIVATE_KEYS})
    if not allowed:
        raise ValueError("public TeVCat dat payload contains no public sources")
    return catalogs, allowed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    first = fetch()
    catalogs, records = extract_public_records(first)
    # Fetch a second complete page before declaring a point-in-time snapshot.
    second = fetch()
    _, final_records = extract_public_records(second)
    first_ids = [row["id"] for row in records]
    final_ids = [row["id"] for row in final_records]
    if first_ids != final_ids:
        raise ValueError("public TeVCat source listing changed during acquisition")
    payload = {"catalogs": catalogs, "sources": records}
    finished = datetime.now(timezone(timedelta(hours=8)))
    group_counts = Counter(str(row["catalog_id"]) for row in records)
    manifest = {
        "schema_version": 1,
        "source_url": BASE_URL,
        "retrieved_at_start": now_utc(),
        "retrieved_at_finish": now_utc(),
        "snapshot_date_shanghai": finished.date().isoformat(),
        "extractor": "public_dat_base64_v1",
        "response_sha256": sha256(first),
        "final_response_sha256": sha256(second),
        "public_payload_sha256": sha256(encoded(payload)),
        "source_count": len(records),
        "source_ids_sha256": sha256(encoded(first_ids)),
        "catalogue_group_counts": dict(sorted(group_counts.items())),
        "private_fields_excluded": sorted(PRIVATE_KEYS),
        "complete": True,
        "notes": [
            "Only records with public=1 are retained.",
            "private_notes and owner are excluded before staging output.",
            "Public site text is not copied into the application catalogue.",
        ],
    }
    write_json(root / "public-sources.json", payload)
    write_json(root / "manifest.json", manifest)
    print(json.dumps({"sources": len(records), "groups": manifest["catalogue_group_counts"], "date": manifest["snapshot_date_shanghai"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
