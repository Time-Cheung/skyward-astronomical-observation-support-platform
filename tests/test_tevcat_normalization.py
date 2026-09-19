"""Regression coverage for the current www.tevcat.org normalized snapshot."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = json.loads((ROOT / "data/catalogues" / "tevcat.json").read_text(encoding="utf-8"))
ASSOCIATIONS = json.loads((ROOT / "data/catalogues" / "tevcat-associations.json").read_text(encoding="utf-8"))


def test_shared_schema_identity_and_public_provenance():
    assert CATALOGUE["schema_version"] == 2
    assert CATALOGUE["catalogue_id"] == "tevcat"
    assert CATALOGUE["label"] == "TeVCat"
    assert CATALOGUE["provenance"]["catalogue_url"] == "https://www.tevcat.org/"
    assert CATALOGUE["provenance"]["source_count"] == len(CATALOGUE["sources"]) == 363
    ids = [source["original_id"] for source in CATALOGUE["sources"]]
    assert len(ids) == len(set(ids)) == 363
    assert all(identifier.isdecimal() for identifier in ids)


def test_coordinates_and_unknown_footprints_stay_evidence_based():
    for source in CATALOGUE["sources"]:
        assert 0 <= source["ra_deg"] < 360
        assert -90 <= source["dec_deg"] <= 90
        assert 0 <= source["l_deg"] < 360
        assert -90 <= source["b_deg"] <= 90
        assert source["planning_radius_deg"] is None
        assert source["footprint_known"] is False
        assert source["footprint_kind"] == "unknown_hard_boundary"


def test_notes_are_minimal_public_facts_not_raw_html_or_private_fields():
    serialized = json.dumps(CATALOGUE, ensure_ascii=False).lower()
    assert "private_notes" not in serialized and '"owner"' not in serialized
    assert "<script" not in serialized and "<br" not in serialized
    for source in CATALOGUE["sources"]:
        notes = source["notes"]
        assert notes["catalogue_source_id"] == source["original_id"]
        assert notes["catalogue_group"]
        assert notes["coordinates"]["frame"] == "FK5"
        assert notes["public_notes"]["rendering"] == "short sanitized public summary; raw HTML not redistributed"
        assert notes["public_notes"]["summary"] is None or "<" not in notes["public_notes"]["summary"]
        assert notes["source_url"].startswith("https://www.tevcat.org/?id=")
        assert "private" not in notes


def test_associations_are_candidate_only_and_non_identity_evidence():
    assert ASSOCIATIONS["verified_associations"] == []
    assert ASSOCIATIONS["provenance"]["method"].startswith("all pairs within fixed angular separation")
    assert all(candidate["status"] == "candidate_only" for candidate in ASSOCIATIONS["candidates"])
    assert all(candidate["evidence"] == [] for candidate in ASSOCIATIONS["candidates"])
