#!/usr/bin/env python3
"""Offline provenance and coverage audit; does not infer physical associations."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def payload_hash(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def audit(root):
    failures = []
    timestamps = []

    def load(name, url):
        path = root / name
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["url"] != url or record["payload_sha256"] != payload_hash(record["data"]):
                raise ValueError("URL or payload hash mismatch")
            timestamps.append(record["retrieved_at"])
            return record["data"]
        except (ValueError, KeyError, OSError) as exc:
            failures.append({"file": name, "error": str(exc)})
            return None

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    base = manifest["base_url"]
    sources = load("sources.json", base + "/api/sources") or []
    final = load("sources_at_finish.json", base + "/api/sources") or []
    source_ids = [s["_id"] for s in sources]
    if len(source_ids) != len(set(source_ids)):
        failures.append({"error": "Duplicate source IDs"})
    if payload_hash(sources) != payload_hash(final):
        failures.append({"error": "Source listing changed"})
    catalogues = load("catalogs.json", base + "/api/catalogs") or []
    observatories = load("observatories.json", base + "/api/observatories") or []
    cats = {s["_id"] for s in catalogues}
    obs = {s["_id"] for s in observatories}
    coverage = Counter()
    epochs = Counter()
    authorities = Counter()
    unresolved = []
    mentions = []
    citation_ids = set()
    all_referenced = set()

    def refs(value):
        found = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "citation_ids" and isinstance(item, list):
                    found.update(cid for cid in item if isinstance(cid, str) and cid)
                else:
                    found.update(refs(item))
        elif isinstance(value, list):
            for item in value:
                found.update(refs(item))
        return found

    def private_keys(value, path=""):
        if isinstance(value, dict):
            for key, item in value.items():
                if "private" in key.lower():
                    failures.append({"source_id": path, "error": "Private key saved: " + key})
                private_keys(item, path)
        elif isinstance(value, list):
            for item in value:
                private_keys(item, path)

    for source in sources:
        sid = source["_id"]
        detail = load("details/" + sid + ".json", base + "/api/sources/" + sid)
        citations = load("citations/" + sid + ".json", base + "/api/sources/" + sid + "/citations")
        if not isinstance(detail, dict) or detail.get("_id") != sid:
            failures.append({"source_id": sid, "error": "Missing or mismatched detail"})
            continue
        coverage["source_details"] += 1
        private_keys(detail, sid)
        if detail.get("catalog_id") not in cats:
            failures.append({"source_id": sid, "error": "Unknown catalogue ID"})
        position = detail.get("position") or {}
        epochs[str(position.get("epoch"))] += 1
        authorities[str(position.get("authority"))] += 1
        coverage["ra_dec_present"] += bool(position.get("ra") and position.get("dec"))
        coverage["public_notes_nonempty"] += bool((detail.get("comment_public") or "").strip())
        coverage["distance_best_nonempty"] += bool((detail.get("distance") or {}).get("best"))
        coverage["morphology_extended_true"] += (detail.get("morphology") or {}).get("is_extended") is True
        flux = detail.get("flux") or {}
        coverage["raw_crab_fraction_positive"] += isinstance(flux.get("crab_fraction"), (int, float)) and flux["crab_fraction"] > 0
        coverage["raw_spectral_index_nonzero"] += bool(flux.get("spectral_index"))
        coverage["structured_spectrum_string_nonempty"] += bool(flux.get("spectrum_string"))
        discoverer = detail.get("discovered_by_id")
        coverage["discovery_instrument_resolved"] += discoverer in obs
        if discoverer and discoverer not in obs:
            failures.append({"source_id": sid, "error": "Discovery instrument not in observatory lookup"})
        cited = refs(detail)
        all_referenced.update(cited)
        if not isinstance(citations, list):
            failures.append({"source_id": sid, "error": "Missing citation array"})
            continue
        coverage["citation_responses"] += 1
        returned = [entry.get("_id") for entry in citations if isinstance(entry, dict)]
        if len(returned) != len(citations) or None in returned or len(returned) != len(set(returned)):
            failures.append({"source_id": sid, "error": "Malformed or duplicate citation ID"})
        citation_ids.update(i for i in returned if i)
        absent = cited - set(returned)
        still_absent = []
        for cid in sorted(absent):
            record = load("references/" + cid + ".json", base + "/api/citations/" + cid)
            if not isinstance(record, dict) or record.get("_id") != cid:
                still_absent.append(cid)
            else:
                citation_ids.add(cid)
        if still_absent:
            unresolved.append({"source_id": sid, "citation_ids": still_absent})
        text = json.dumps({k: detail.get(k) for k in ["names", "comment_public", "other_catalogs"]}, ensure_ascii=False)
        if "2lhaaso" in text.lower():
            mentions.append({"source_id": sid, "name": source["name"], "url": base + "/sources/" + sid,
                             "status": "Textual mention only; requires association evidence review"})

    complete = (bool(manifest.get("complete")) and not failures and not unresolved
                and len(sources) == manifest.get("expected_sources") == manifest.get("expected_count_guard"))
    return {"acquisition_validated": complete, "scientifically_reviewed": False,
            "source_count": len(sources), "unique_source_count": len(set(source_ids)),
            "catalogue_groups": dict(Counter(s["catalog"] for s in sources)),
            "field_coverage": dict(coverage), "epochs": dict(epochs), "coordinate_authorities": dict(authorities),
            "unique_citations": len(citation_ids), "referenced_citation_ids": len(all_referenced),
            "unresolved_per_source_references": unresolved,
            "globally_unresolved_reference_ids": sorted(all_referenced - citation_ids),
            "earliest_page_retrieved_at": min(timestamps) if timestamps else None,
            "latest_page_retrieved_at": max(timestamps) if timestamps else None,
            "two_lhaaso_textual_mentions": mentions, "failures": failures,
            "notes": ["Coverage reports field presence, not scientific validity.",
                      "Zero values in the upstream schema can be placeholders; do not infer zero physical flux/distance or zero uncertainty.",
                      "2LHAASO textual mentions are not verified source associations.",
                      "A successful acquisition audit does not authorize redistribution of site prose or scientific papers."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = audit(args.directory)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["acquisition_validated"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
