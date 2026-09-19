from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def test_tevcat_www_snapshot_is_public_and_minimized():
    catalogue = json.loads((ROOT / "data/catalogues/tevcat.json").read_text(encoding="utf-8"))
    serialized = json.dumps(catalogue, ensure_ascii=False).lower()
    assert catalogue["schema_version"] == 2
    assert catalogue["provenance"]["catalogue_url"] == "https://www.tevcat.org/"
    assert len(catalogue["sources"]) == 363
    assert catalogue["provenance"]["catalogue_group_counts"] == {"1": 304, "2": 33, "3": 10, "4": 16}
    assert "private_notes" not in serialized
    assert '"owner"' not in serialized
    assert "<script" not in serialized


def test_tevcat_detail_has_readable_normalized_notes_and_no_date_name_suffix():
    client = TestClient(app)
    listing = client.get("/api/v1/sources", params={"catalog_tokens": "tevcat", "limit": 1}).json()
    row = listing["sources"][0]
    assert row["display_name"].startswith("TeVCat ")
    assert "截止" not in row["display_name"]
    detail = client.get("/api/v1/sources/" + row["source_key"]).json()
    notes = detail["notes"]
    assert notes["catalogue_source_id"].isdigit()
    assert notes["catalogue_group"]
    assert "coordinates" in notes and "physical_fields" in notes
    assert "public_notes" in notes and "summary" in notes["public_notes"]


def test_tevcat_metadata_exposes_localized_picker_labels():
    client = TestClient(app)
    row = next(item for item in client.get("/api/v1/catalogues").json()["catalogues"] if item["identifier"] == "tevcat")
    assert row["count"] == 363
    assert row["display"]["zh"].startswith("TeVCat（截止到")
    assert row["display"]["en"] == "TeVCat (as of 2026-09-19)"
