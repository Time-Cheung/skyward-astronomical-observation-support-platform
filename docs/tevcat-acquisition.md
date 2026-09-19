# TeVCat public snapshot acquisition

Skyward's installed TeVCat table is a minimal normalized snapshot of the public data embedded by [www.tevcat.org](https://www.tevcat.org/). It is not a mirror of the web page, a bibliography archive, or an identity cross-match catalogue.

## Reproducible acquisition

Run from the repository root with the project virtual environment:

```bash
.venv/bin/python scripts/fetch_tevcat_www.py --output /secure/staging/tevcat-www-YYYYMMDD
.venv/bin/python scripts/build_tevcat_www_catalogue.py --staging /secure/staging/tevcat-www-YYYYMMDD
```

The fetcher retrieves the public page twice under certificate verification, decodes the public embedded `dat` payload, and stops if the public source ID list changes during acquisition. The repository does not contain the fetched HTML.

The staging manifest records retrieval timestamps, Shanghai snapshot date, public response and payload hashes, source-ID hash, source/group counts, and extractor version. The builder converts only public structured records to `data/catalogues/tevcat.json` and creates a separate proximity-only association audit.

## Privacy and scientific boundaries

- Non-public/operator fields, including private notes and ownership fields, are removed before staging output.
- Raw public notes HTML, long web-page prose, and papers are not redistributed. The normalized table retains only availability/digest metadata and a source URL.
- Reported extension or morphology fields are catalogue facts, not verified hard planning footprints. Every imported TeVCat record therefore has `planning_radius_deg: null`, `footprint_known: false`, and is evaluated only as a centre source unless an operator makes an explicit nominal-radius request.
- Positional proximity with a 2LHAASO target is a candidate-only audit result, never an identity match or automatic association.

The actual snapshot date, total, group counts, hashes, and field policy are available in the catalogue's `provenance` and in the external staging manifest.
