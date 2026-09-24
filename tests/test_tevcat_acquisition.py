"""Offline tests of the public TeVCat acquisition boundary (no astronomy imports)."""
import json
import ssl

import httpx
import pytest

from scripts.fetch_tevcat import BASE, Fetcher, digest, encoded, save, scrub, project, main
from scripts.validate_tevcat import audit, payload_hash


def test_scrub_retains_coordinate_authority_but_removes_private_data():
    result = scrub({"position": {"authority": "RA/Dec", "epoch": "J2000"},
                    "comment_private": "DO NOT SAVE", "auth": {"token": "secret"},
                    "comment_public": "Public scientific notes", "items": [{"session_id": "secret", "ra": 0}]})
    assert result == {"position": {"authority": "RA/Dec", "epoch": "J2000"},
                      "comment_public": "Public scientific notes", "items": [{"ra": 0}]}


def test_encoding_does_not_silently_write_nan():
    with pytest.raises(ValueError):
        encoded({"flux": float("nan")})


@pytest.fixture
def fetcher(tmp_path):
    f = Fetcher(tmp_path)
    yield f
    f.client.close()


def test_detail_projection_and_checkpoint_integrity(fetcher, monkeypatch):
    raw = encoded({"_id": "source1", "name": "Test", "position": {"authority": "RA/Dec"},
                   "names": {"common": "Test"}, "citation_ids": [], "catalog_id": "c1",
                   "comment_private": "never publish", "unknown_admin_field": "do not copy"})
    monkeypatch.setattr(fetcher, "request", lambda path: (raw, "application/json"))
    data = fetcher.get("/api/sources/source1", "details/source1.json", "detail")
    assert data["position"]["authority"] == "RA/Dec"
    assert "comment_private" not in data
    assert "unknown_admin_field" not in data
    wrapper = json.loads((fetcher.output / "details/source1.json").read_text())
    assert wrapper["response_sha256"] == digest(raw)
    assert wrapper["payload_sha256"] == digest(encoded(data))
    monkeypatch.setattr(fetcher, "request", lambda path: pytest.fail("checkpoint should avoid network"))
    assert fetcher.get("/api/sources/source1", "details/source1.json", "detail") == data
    wrapper["data"]["name"] = "tampered"
    save(fetcher.output / "details/source1.json", wrapper)
    with pytest.raises(ValueError, match="hash mismatch"):
        fetcher.get("/api/sources/source1", "details/source1.json", "detail")


def test_wrong_source_id_is_not_saved(fetcher, monkeypatch):
    monkeypatch.setattr(fetcher, "request", lambda path: (b'{"_id":"wrong"}', "application/json"))
    with pytest.raises(ValueError, match="Source ID mismatch"):
        fetcher.get("/api/sources/expected", "details/expected.json", "detail")
    assert not (fetcher.output / "details/expected.json").exists()


def test_html_success_is_not_a_json_success(fetcher, monkeypatch):
    monkeypatch.setattr(fetcher, "request", lambda path: (b"<html>application shell</html>", "text/html"))
    with pytest.raises(ValueError, match="Expected JSON"):
        fetcher.get("/api/sources", "sources.json")


def test_citations_keep_metadata_not_full_papers(fetcher, monkeypatch):
    raw = encoded([{"_id": "c1", "title": "Scientific work", "bibcode": "2008ICRC....3.1341W",
                    "url": "https://example.org/paper", "abstract": "not copied", "bibhash": {"full": "not copied"}}])
    monkeypatch.setattr(fetcher, "request", lambda path: (raw, "application/json"))
    data = fetcher.get("/api/sources/s1/citations", "citations/s1.json", "citations")
    assert data == [{"_id": "c1", "title": "Scientific work", "bibcode": "2008ICRC....3.1341W",
                     "url": "https://example.org/paper"}]


def test_robots_html_fallback_and_disallow(fetcher, monkeypatch):
    monkeypatch.setattr(fetcher, "request", lambda path: (b"<html>SPA</html>", "text/html"))
    fetcher.rules()
    assert fetcher.robots is None
    monkeypatch.setattr(fetcher, "request", lambda path: (b"User-agent: *\nDisallow: /api/\n", "text/plain"))
    fetcher.rules()
    assert not fetcher.robots.can_fetch("Skyward-CatalogueSnapshot", BASE + "/api/sources")


def test_tls_checks_enabled(fetcher):
    context = fetcher.client._transport._pool._ssl_context
    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert not fetcher.client.follow_redirects


@pytest.mark.parametrize("mode,data", [
    ("detail", {"_id": "wrong"}),
    ("citations", {"_id": "c1"}),
    ("citations", [{"_id": "c1"}, {"_id": "c1"}]),
    ("citations", [{"_id": "c1", "comment_private": "secret"}]),
])
def test_resumed_checkpoints_revalidated(fetcher, mode, data):
    path = "/api/sources/s1" + ("/citations" if mode == "citations" else "")
    save(fetcher.output / "cache.json", {"url": BASE + path, "payload_sha256": digest(encoded(data)), "data": data})
    with pytest.raises(ValueError):
        fetcher.get(path, "cache.json", mode)


@pytest.mark.parametrize("problem", ["truncated", "missing_reference", "metadata_failure", "success"])
def test_main_completion_guards(tmp_path, monkeypatch, problem):
    import sys
    monkeypatch.setattr(sys, "argv", ["fetch_tevcat", "--output", str(tmp_path), "--expected-count", "1"])
    monkeypatch.setattr(Fetcher, "rules", lambda self: None)
    def fake_get(self, path, filename, mode="plain", refresh=False):
        if path == "/api/catalogs" and problem == "metadata_failure":
            raise ValueError("Broken metadata response")
        if path == "/api/sources":
            if problem == "truncated":
                return [{"_id": "s1", "catalog": "Default Catalog"}, {"_id": "s2", "catalog": "Default Catalog"}]
            return [{"_id": "s1", "catalog": "Default Catalog"}]
        if path.endswith("/citations"):
            return [] if problem == "missing_reference" else [{"_id": "c1"}]
        if mode == "citation" and problem == "missing_reference":
            raise ValueError("Missing referenced citation")
        if mode == "detail":
            return {"_id": "s1", "citation_ids": ["c1"]}
        return []
    monkeypatch.setattr(Fetcher, "get", fake_get)
    result = main()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    if problem == "success":
        assert result == 0 and manifest["complete"]
    else:
        assert result == 2 and not manifest["complete"]
        assert manifest["failures"]
        if problem == "metadata_failure":
            assert manifest["failures"][0]["stage"] == "/api/catalogs"


def test_audit_blocks_unpublished_2lhaaso_text(tmp_path):
    base = "https://example.test"

    def checkpoint(relative, url, data):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "url": url, "payload_sha256": payload_hash(data),
            "retrieved_at": "2026-09-24T00:00:00Z", "data": data,
        }), encoding="utf-8")

    source = {"_id": "s1", "name": "Test", "catalog": "C"}
    detail = {
        "_id": "s1", "catalog_id": "c1",
        "position": {"ra": "1", "dec": "2", "epoch": "J2000", "authority": "RA/Dec"},
        "names": ["2LHAASO JTEST"], "comment_public": "",
        "other_catalogs": [], "citation_ids": [],
    }
    (tmp_path / "manifest.json").write_text(json.dumps({
        "base_url": base, "complete": True,
        "expected_sources": 1, "expected_count_guard": 1,
    }), encoding="utf-8")
    checkpoint("sources.json", base + "/api/sources", [source])
    checkpoint("sources_at_finish.json", base + "/api/sources", [source])
    checkpoint("catalogs.json", base + "/api/catalogs", [{"_id": "c1"}])
    checkpoint("observatories.json", base + "/api/observatories", [])
    checkpoint("details/s1.json", base + "/api/sources/s1", detail)
    checkpoint("citations/s1.json", base + "/api/sources/s1/citations", [])

    result = audit(tmp_path)
    assert result["acquisition_validated"] is False
    assert result["forbidden_two_lhaaso_textual_mentions"][0]["source_id"] == "s1"
    assert any("Unpublished 2LHAASO" in row.get("error", "") for row in result["failures"])
