#!/usr/bin/env python3
"""Checkpoint the public TeVCat API without disabling TLS or downloading papers.

Staging only: a successful acquisition is not scientific verification or approval
for redistribution. Review and normalize these records before app integration.
Run with the project's existing httpx/certifi dependencies. No app import needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.robotparser import RobotFileParser

import certifi
import httpx

BASE = "https://tevcat2.tevcat.org"
MAX_BYTES = 8 * 1024 * 1024
DETAIL_KEYS = {
    "_id", "catalog_id", "citation_ids", "comment_public", "created_at",
    "deleted_at", "discovered_by_id", "discovery_date", "distance",
    "distance_wanted", "flux", "is_fgst", "morphology", "name", "names",
    "other_catalogs", "position", "seen_by_ids", "source_type_id",
    "type_tag_ids", "updated_at", "wavebands", "source_type_id_data",
    "type_tags_data", "catalog_id_data", "seen_by_ids_data",
}
CITATION_KEYS = {
    "_id", "author", "bibcode", "date", "journal", "title", "type", "url",
    "updated_at",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def scrub(value):
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()
                if not any(word in k.lower() for word in ("private", "password", "token", "session"))
                and k.lower() not in {"auth", "authorization", "authentication"}}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def referenced_citations(value):
    if isinstance(value, dict):
        raw_ids = value.get("citation_ids") or []
        if not isinstance(raw_ids, list):
            raise ValueError("Citation identifiers must be an array")
        result = {cid for cid in raw_ids if cid not in (None, "")}
        if any(not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", cid) for cid in result):
            raise ValueError("Unsafe citation identifier")
        for key, item in value.items():
            if key != "citation_ids":
                result.update(referenced_citations(item))
        return result
    if isinstance(value, list):
        return set().union(*(referenced_citations(item) for item in value))
    return set()


def project(value, mode, path):
    """Validate both fresh responses and resumed checkpoints identically."""
    if mode == "detail":
        if not isinstance(value, dict) or value.get("_id") != path.split("/")[-1]:
            raise ValueError("Source ID mismatch")
        if not isinstance(value.get("position"), dict) or not isinstance(value.get("names"), dict):
            raise ValueError("Missing source coordinate/name object")
        if not isinstance(value.get("citation_ids"), list) or not isinstance(value.get("catalog_id"), str):
            raise ValueError("Missing source citation/catalogue identifiers")
        value = {k: v for k, v in value.items() if k in DETAIL_KEYS}
    elif mode == "citation":
        if not isinstance(value, dict) or value.get("_id") != path.split("/")[-1]:
            raise ValueError("Citation ID mismatch")
        value = {k: v for k, v in value.items() if k in CITATION_KEYS}
    elif mode == "citations":
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise ValueError("Expected citation object array")
        ids = [item.get("_id") for item in value]
        if any(not isinstance(cid, str) or not cid for cid in ids) or len(ids) != len(set(ids)):
            raise ValueError("Missing or duplicate citation ID")
        value = [{k: v for k, v in item.items() if k in CITATION_KEYS} for item in value]
    return scrub(value)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replaced only within this dedicated acquisition directory.
    pending = path.with_suffix(path.suffix + ".partial")
    pending.write_bytes(encoded(value) + b"\n")
    pending.replace(path)


class Fetcher:
    def __init__(self, output, interval=0.5):
        self.output = output
        self.interval = interval
        self.last = 0.0
        self.robots = None
        # Explicit trusted CA bundle; CERT_REQUIRED and hostname checking remain on.
        self.client = httpx.Client(
            verify=ssl.create_default_context(cafile=certifi.where()),
            timeout=httpx.Timeout(30, connect=15), follow_redirects=False,
            headers={"User-Agent": "Skyward-CatalogueSnapshot/1.0 (public astronomy data; serial acquisition)"},
        )

    def request(self, path):
        if self.robots and not self.robots.can_fetch("Skyward-CatalogueSnapshot", BASE + path):
            raise ValueError("Disallowed by robots.txt: " + path)
        for attempt in range(3):
            time.sleep(max(0, self.interval - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                with self.client.stream("GET", BASE + path) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_BYTES:
                            raise ValueError("Response exceeds byte limit")
                    return bytes(raw), response.headers.get("content-type", "")
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (429, 500, 502, 503, 504):
                    raise
                if attempt == 2:
                    raise
                delay = 2 ** (attempt + 1)
                if isinstance(exc, httpx.HTTPStatusError):
                    retry_after = exc.response.headers.get("retry-after", "")
                    if retry_after.isdigit():
                        delay = max(delay, int(retry_after))
                time.sleep(min(120, delay))

    def get(self, path, filename, mode="plain", refresh=False):
        target = self.output / filename
        if target.is_file() and not refresh:
            wrapper = json.loads(target.read_text())
            if wrapper.get("url") != BASE + path or wrapper.get("payload_sha256") != digest(encoded(wrapper["data"])):
                raise ValueError("Checkpoint provenance or hash mismatch: " + filename)
            value = project(wrapper["data"], mode, path)
            if encoded(value) != encoded(wrapper["data"]):
                raise ValueError("Checkpoint has unapproved/private fields: " + filename)
            return value
        raw, content_type = self.request(path)
        if "json" not in content_type:
            raise ValueError("Expected JSON, got " + content_type)
        value = json.loads(raw)
        value = project(value, mode, path)
        save(target, {"url": BASE + path, "retrieved_at": now(),
                      "response_sha256": digest(raw), "payload_sha256": digest(encoded(value)),
                      "data": value})
        return value

    def rules(self):
        raw, kind = self.request("/robots.txt")
        text = raw.decode("utf-8", errors="replace")
        status = "no_rules_html_spa_fallback"
        if "user-agent:" in text.lower() and "<html" not in text.lower():
            self.robots = RobotFileParser()
            self.robots.parse(text.splitlines())
            status = "parsed"
            delay = self.robots.crawl_delay("Skyward-CatalogueSnapshot")
            rate = self.robots.request_rate("Skyward-CatalogueSnapshot")
            self.interval = max(self.interval, delay or 0, rate.seconds / rate.requests if rate and rate.requests else 0)
        save(self.output / "robots_check.json", {"url": BASE + "/robots.txt",
             "retrieved_at": now(), "content_type": kind, "sha256": digest(raw), "status": status})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Dedicated staging directory, not published app data")
    parser.add_argument("--interval", type=float, default=0.5, help="Minimum seconds between serial request starts (>=0.5)")
    parser.add_argument("--expected-count", type=int, required=True, help="Independently checked official source count; guards against silent API truncation")
    args = parser.parse_args()
    if args.expected_count < 1:
        parser.error("--expected-count must be positive")
    if args.interval < 0.5:
        parser.error("--interval must be >=0.5")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    report = {"schema_version": 1, "base_url": BASE, "acquisition_started_at": old.get("acquisition_started_at", now()),
              "status": "incomplete", "complete": False, "failures": [],
              "attribution": "Wakely & Horan (2008), ICRC 3, 1341-1344, 2008ICRC....3.1341W",
              "review_status": "Unreviewed staging data; not yet integrated or approved for publication"}
    save(manifest_path, report)
    fetcher = Fetcher(output, args.interval)
    stage = "/robots.txt"
    try:
        fetcher.rules()
        for path, filename in [("/api/catalogs", "catalogs.json"), ("/api/sourcetypes", "types.json"),
                               ("/api/observatories", "observatories.json")]:
            stage = path
            fetcher.get(path, filename)
        stage = "/api/sources"
        sources = fetcher.get("/api/sources", "sources.json")
        if not isinstance(sources, list) or not sources:
            raise ValueError("Missing source array")
        if len(sources) != args.expected_count:
            raise ValueError(f"Expected {args.expected_count} independently checked sources, received {len(sources)}")
        ids = [item["_id"] for item in sources]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", sid) for sid in ids):
            raise ValueError("Duplicate or unsafe source ID")
        report.update(expected_sources=len(ids), catalogue_groups=dict(Counter(item["catalog"] for item in sources)),
                      expected_count_basis="Operator/developer checked official listing; explicit CLI guard",
                      expected_count_guard=args.expected_count, details_succeeded=0, citations_succeeded=0)
        supplementary = set()
        for index, source in enumerate(sources, start=1):
            sid = source["_id"]
            pair = {}
            for suffix, folder, mode in [("", "details", "detail"), ("/citations", "citations", "citations")]:
                path = "/api/sources/" + sid + suffix
                try:
                    stage = path
                    pair[mode] = fetcher.get(path, folder + "/" + sid + ".json", mode)
                    report["details_succeeded" if mode == "detail" else "citations_succeeded"] += 1
                except (httpx.HTTPError, ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
                    report["failures"].append({"source_id": sid, "url": BASE + path, "error": str(exc)[:500]})
            if "detail" in pair and "citations" in pair:
                expected_refs = referenced_citations(pair["detail"])
                received_refs = {item["_id"] for item in pair["citations"]}
                missing = expected_refs - received_refs
                for cid in sorted(missing):
                    citation_path = "/api/citations/" + cid
                    stage = citation_path
                    try:
                        fetcher.get(citation_path, "references/" + cid + ".json", "citation")
                        supplementary.add(cid)
                    except (httpx.HTTPError, ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
                        report["failures"].append({"source_id": sid, "url": BASE + citation_path,
                                                  "error": str(exc)[:500], "citation_id": cid})
                report["supplemental_citations_succeeded"] = len(supplementary)
            report["last_checked_at"] = now()
            save(manifest_path, report)
            if index % 20 == 0 or index == len(sources):
                print(json.dumps({"processed": index, "total": len(sources), "failures": len(report["failures"])}), flush=True)
        stage = "/api/sources (final check)"
        final_list = fetcher.get("/api/sources", "sources_at_finish.json", refresh=True)
        report["listing_unchanged"] = encoded(sources) == encoded(final_list)
        if not report["listing_unchanged"]:
            report["failures"].append({"error": "Source listing changed during acquisition; review before marking complete"})
        report["complete"] = not report["failures"]
        report["status"] = "acquired_not_scientifically_reviewed" if report["complete"] else "incomplete"
        report["acquisition_finished_at"] = now()
        if report["complete"]:
            report["acquisition_date_shanghai"] = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        save(manifest_path, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        return 0 if report["complete"] else 2
    except (httpx.HTTPError, ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        report["complete"] = False
        report["status"] = "failed"
        report["failures"].append({"stage": stage, "error": str(exc)[:500]})
        report["last_checked_at"] = now()
        save(manifest_path, report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        return 2
    finally:
        fetcher.client.close()


if __name__ == "__main__":
    raise SystemExit(main())
