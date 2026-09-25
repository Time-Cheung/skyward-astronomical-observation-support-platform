# Skyward IT Deployment Guide (English)

[中文](DEPLOYMENT.zh-CN.md) · [User guide](README.en.md) · [Development](DEVELOPMENT.en.md)

## 1. Security boundary and release contents

The current V2.2 (2.2.20260924) has no login, tenant isolation, or authorization and must never be exposed publicly. Prefer loopback-only binding. LAN access requires administrator-approved source-CIDR restrictions and a negative test from an unapproved network. Only the server installs Python dependencies; clients need a browser.

/opt/skyward, user skyward, 192.168.50.10, 192.168.50.0/24, and port 8000 below are replaceable examples. The validated baseline is Python 3.9.x, NumPy 1.26.4, and Astropy 6.0.1; requirements.txt is authoritative. A release includes code, data, deployment templates, docs, scripts, tests, dependency pins, and provenance. V2.2 must use the public Table 2 normalization at `data/catalogues/1lhaaso.json`; the release tree, source archive, and current GitHub tree must not contain the original `data/2LHAASO.txt`, and `/api/v1/catalogues` must not expose `2lhaaso`.

A formal archive is created only after the user explicitly publishes a new version. Its name is skyward-v<major.minor>.zip; full version 2.2.20260924 maps to skyward-v2.2.zip. The filename omits the date, while the archive records the full version, date, Git state, manifest, and hashes. The current release is full version 2.2.20260924, packaged as skyward-v2.2.zip.

## 2. Install and release gate

The current V2.2 (2.2.20260924) includes per-catalogue icons, batch target-list calculations, tracked-FoV curves, sorted windows, and plan-preview sorting. CSV formats remain documented on the Data notes page: source catalogues require at least `name,ra,dec`, while batch target lists require `name,ra,dec,ext`; all are UTF-8.

~~~bash
cd /opt/skyward
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); print(numpy.__version__,astropy.__version__)'
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib"
export SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
node --check app/static/app.js
git diff --check
~~~

Any failure blocks deployment. Do not mix global NumPy 2.x or use sudo pip.

## 3. Local and controlled LAN

Recommended server-local mode:

~~~bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/config
ss -ltnp | grep ':8000'
~~~

For LAN mode, an administrator first confirms the real server IP/interface, trusted client CIDR, VLAN/ACL, and firewall manager, then permits TCP 8000 only from approved sources. Prefer a specific private binding:

~~~bash
.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000
~~~

Clients browse the server's real address, such as http://192.168.50.10:8000/. 0.0.0.0 is a listener, not a destination, and client loopback is not the server. Never disable the firewall to troubleshoot.

## 4. systemd

Review exactly one of deploy/skyward-local.service and deploy/skyward-lan.service. Replace user, group, working directory, absolute Python path, cache directories, and LAN IP. Do not run both on one port.

~~~bash
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward/matplotlib /var/cache/skyward/data
sudo install -m 0644 deploy/skyward-local.service /etc/systemd/system/skyward.service
sudo systemctl daemon-reload
sudo systemctl enable --now skyward.service
systemctl status skyward.service --no-pager
journalctl -u skyward.service -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/api/v1/health
~~~

## 5. Offline and egress policy

On a connected host matching the target architecture and Python ABI:

~~~bash
python3 -m venv .venv-wheelbuild
.venv-wheelbuild/bin/python -m pip download --only-binary=:all: -r requirements.txt -d wheelhouse
sha256sum requirements.txt wheelhouse/* > wheelhouse.sha256
~~~

Transfer the release, wheelhouse, hashes, data, and provenance through controlled media. Run sha256sum -c wheelhouse.sha256, then pip install --no-index --find-links ./wheelhouse -r requirements.txt. Do not copy .venv across platforms.

Static assets, local catalogues, and geometry inside IERS coverage can run offline. New Gaia queries require approved server DNS/TLS egress and occur only on the result local map. Defaults are 1°, 10 rows, and G≤10; configurable bounds are 0.1–5°, 1–500 rows, and G≤5–22, with two concurrent queries, 2 MiB responses, and 32 exact-parameter process-cache entries. Default or smaller requests use synchronous TAP with a 30-second timeout. A request broader, deeper, or larger than the defaults checks cache first and then uses asynchronous TAP with a 30-second total budget. A synchronous timeout may use at most five bounded half-radius subcones with a 50-second total budget; output may be incomplete after fallback but is ordered by angular distance before return. Failure is not successful zero rows.

IERS startup selects a fresh cache or bundled table and attempts a bounded background refresh. auto_download=False does not disable this application refresh; seven days is cache freshness, not a scheduler. Inspect source_kind, coverage dates, covers_current_time, and attempt/success/error timestamps. Out-of-coverage planning can return 422.

## 6. Functional and network acceptance

- Read /api/v1/health JSON and verify IERS coverage; HTTP 200 alone is insufficient.
- /api/v1/catalogues is the source of truth for the currently installed catalogue identifiers and record counts; Gaia reports selection_scope=result_local_fov_only.
- Home and result all-sky views have no Gaia choice, layer, legend, or current-map request.
- The result local view shows a 10° region and separate 8.3° LACT dashed FoV. All-sky and local maps share Real-time / Observation window / Specified time plus purple tracked-source outlines. No current-FoV constraint is applied because authoritative live pointing is unavailable.
- Enabling Gaia sends a local-fov request with the UI filters (default 1°, G≤10, 10 sources, selecting the nearest sources by angular distance when needed), draws Gaia candidates as thicker red/green crosses under the shared state, reports red/green counts, and preserves catalogue markers; disabling removes only Gaia.
- Calculate a short range with multiple full-footprint windows. Each valid window must have a checked-by-default selector, and the list must expose exactly one Add, Preview, and Download action group. Clear one selector, add the remainder, and confirm Preview shows one plan entry with the remaining windows; alternative-screening status must identify each window. The ZIP must contain an office-readable XLSX with a solid black header, one yellow target row per selected window followed by green alternative rows, and, when plots are selected, paired local-FoV and observing-window SVGs for every plan entry.
- After changing mode, zoom, Gaia, or comparison curves, open Data notes/API and click “Sky map & planner”; the current DOM should restore directly without a window calculation or either map request. The current target's details should not show “Use for planning”; other ordinary-source details should retain it.
- In LAN mode test approved and unapproved networks and confirm no public forwarding.

## 7. Upgrade and rollback

Never overwrite a dirty production checkout. Prefer a separate candidate directory; use git pull --ff-only only for a clean in-place checkout. Record the current commit, unit, dependencies, data hashes, and recoverable backup. Restart the actual service only after all gates pass in an authorized maintenance window, then hard-refresh clients.

Rollback restores code, data, pinned environment, unit, and provenance together. Git does not restore untracked data, caches, or .venv; do not use destructive cleaning to erase changes. Repeat pip check, full pytest, health checks, and network acceptance before restoration.

## Copyright and developer

Copyright © 2026 Wei Zhang. All rights reserved.

Developer: **Wei Zhang (张炜)**, Postdoctoral Researcher at the Institute of High Energy Physics, Chinese Academy of Sciences (IHEP-CAS). The affiliation is provided for identification only and does not imply institutional ownership or endorsement.
