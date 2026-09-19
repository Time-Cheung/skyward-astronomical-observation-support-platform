# Skyward User and Deployment Guide (English)

[中文](../zh/使用与部署手册.md) · [Offline installation](../offline-deployment.md)

## 0. For experienced operators: shortest path

**Choose A (server-local only) or B (controlled LAN); do not run both on port 8000.** The current adapter is LACT and results are geometry-only candidate windows. There are no accounts or authorization boundaries. Never publish this service to the Internet. Only the server installs dependencies and contacts optional IERS/Gaia services; clients need a browser and connectivity to the server.

**Every path, user, group, IP, CIDR, interface and service name below is an example to replace**, not a claim about the current machine. Examples: project `/opt/skyward`, user/group `skyward`, Python `/opt/python-3.9.21/bin/python3`, server LAN IP `192.168.50.10`, approved client CIDR `192.168.50.0/24`, port `8000`.

Python **3.9.21 is the validated version**. The interpreter path and Conda command below reproduce that environment; this is not the only deployable patch version. Other compatible Python versions require the same pinned dependencies and a fresh full test run; compatibility with arbitrary newer versions is not implied.

Acquire the code first; choose one option. Replace `REPOSITORY_URL` with the maintainer-approved repository URL and have the administrator grant the deployment user access to the parent directory. For an existing production checkout, follow Section 8 in a maintenance window, preferably using a separate candidate directory. Back up local edits; do not automatically stash, reset, clean or overwrite them.

```bash
# First checkout: destination must not already exist
git clone REPOSITORY_URL /opt/skyward
```

```bash
# Existing checkout: inspect and fast-forward only when clean
cd /opt/skyward
git status --short
if [ -z "$(git status --porcelain)" ]; then git pull --ff-only; else echo 'STOP: preserve local changes first'; fi
```

Stop on local edits, divergent history or pull failure; preserve changes and resolve manually. Continue only after success. On an isolated host use an approved transferred release instead of online clone/pull.

```bash
# Common preparation: on the server, as owner of the project/runtime directories
cd /opt/skyward
/opt/python-3.9.21/bin/python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); assert numpy.__version__=="1.26.4"; assert astropy.__version__=="6.0.1"; print(sys.executable, numpy.__version__, astropy.__version__)'
mkdir -p .runtime/matplotlib .runtime/cache
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
# Full suite, not just smoke tests; retain output and exit status
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
```

- **A local:** `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; browse `http://127.0.0.1:8000/` **on the server**, and check `/api/v1/health` there.
- **B LAN:** apply Section 4's source-restricted firewall first, then `.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000`; server and authorized clients browse `http://192.168.50.10:8000/`, substituting the server's actual LAN IP. Use `--host 0.0.0.0` only behind an already verified trusted-subnet firewall.
- Persistent service templates: `deploy/skyward-local.service` and `deploy/skyward-lan.service`. Test manually, stop that foreground process, then follow the appropriate installation section. These are instructions: **this documentation change has not installed, started, stopped or replaced any existing service or changed the firewall**.

## 1. Beginner tutorial: server, client and boundaries

The server is the Linux host running Skyward. A client is a computer opening its website. Clients do not install Python, Conda, NumPy or catalogues and do not need direct Internet access to Gaia/IERS. Only optional server-side online features require approved outbound access. Offline geometry uses local data.

`127.0.0.1` always means the machine making the request: a client's loopback is not the server. `0.0.0.0` means listening on all IPv4 interfaces; **it is not a browser destination**. Binding a private IP does not identify trusted clients, so a firewall remains necessary. Never forward this port to the Internet, expose it through a public reverse proxy, permit all source networks or disable the firewall to troubleshoot.

The current LACT site is `100.0266666667° E`, `29.3575° N`, altitude `4410 m`, with an ideal circular `8.3°` diameter FoV and a fixed-zenith reference until telemetry is connected. Weather, clouds, aerosols, equipment state, mechanical limits, tracking error, real response/sensitivity and joint-observation acceptance are not evaluated. A green status or candidate window is not observing approval.

## 2. Common preparation (required for both A and B)

1. Acquire the trusted release using Section 0's first-clone or existing-checkout procedure (approved transfer when offline). Obtain a Linux host, Python (validated **3.9.21**; retest other compatible versions) and permissions from your administrator. If using a different project path, replace it everywhere, including unit files. Do not run the web service as root.
2. Ensure the deployment user/group exist and can traverse parent directories and read code/data. Manual execution needs a writable `.runtime/`; systemd uses `/var/cache/skyward-local` or `/var/cache/skyward-lan`. Do not make the entire project world-writable.
3. Run **all common preparation commands in Section 0** on the server. The project `.venv` is the default runtime. Avoid `sudo pip` and unqualified `pip/uvicorn`, which can mix in global NumPy 2.x. `requirements.txt` remains unchanged, including pinned **NumPy 1.26.4 and Astropy 6.0.1**.
4. Include the data package, catalogue provenance and `data/iers/finals2000A.all`, not just source code. Planned times must be covered by the active IERS table. For an isolated server, prepare a wheelhouse as described in the [offline supplement](../offline-deployment.md).
5. A nonzero full-pytest exit status blocks release. Keep logs and investigate. This document gives commands and acceptance criteria; it **does not assert that all features have passed final release acceptance**.

### Optional Conda alternative (do not mix runtimes)

If your administrator chooses Conda, replace `.venv` with one isolated environment:

```bash
conda create -n skyward python=3.9.21 pip
conda activate skyward
python -m pip install -r requirements.txt
python -m pip check
python -c 'import sys,numpy,astropy; print(sys.version); assert numpy.__version__=="1.26.4"; assert astropy.__version__=="6.0.1"; print(sys.executable)'
```

Replace every subsequent `.venv/bin/python` with this environment's **absolute Python path**, for example `/opt/miniforge/envs/skyward/bin/python` (replace it). Adjust `ExecStart` too. systemd does not depend on a shell's `conda activate`. Do not install into both environments.

## 3. Deployment A: server-local access only

### A1. Start manually and check

After common preparation, run on the server:

```bash
cd /opt/skyward
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep that terminal open. In a second server terminal:

```bash
ss -ltnp | grep ':8000'
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/config
```

Open `http://127.0.0.1:8000/` in a browser **on the server**. On a headless server start with curl; do not silently change to an all-interface listener just to see the page. Expect only `127.0.0.1:8000`, not `0.0.0.0:8000`, `[::]:8000` or a LAN listener. **A requires no LAN firewall opening for port 8000.**

### A2. Optional persistent systemd service

`skyward-local.service` is the example service name actually used in the commands below. Inspect existing services first to avoid overwriting one. Review and replace `User`, `Group`, `WorkingDirectory`, `ExecStart` and cache paths in the template. Examples use user/group `skyward` and project `/opt/skyward`.

Stop the foreground process above with Ctrl+C. An authorized administrator may then run:

```bash
cd /opt/skyward
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward-local
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward-local/matplotlib /var/cache/skyward-local/data
sudo -u skyward test -w /var/cache/skyward-local/matplotlib
sudo -u skyward test -w /var/cache/skyward-local/data
sudo install -m 0644 deploy/skyward-local.service /etc/systemd/system/skyward-local.service
sudo systemctl daemon-reload
sudo systemctl enable --now skyward-local.service
systemctl status skyward-local.service --no-pager
journalctl -u skyward-local.service -n 100 --no-pager
ss -ltnp | grep ':8000'
curl -fsS http://127.0.0.1:8000/api/v1/health
```

Both `MPLCONFIGDIR` and `SKYWARD_CACHE_DIR` are inside the service's writable cache root; IERS uses `iers/` beneath the latter. Templates do not require a writable home or shared writable `/tmp`. The legacy `lact-window-planner.service` template now also defaults to loopback: explicitly choose the LAN template for B. Changing a repository template does not change an already installed service.

### A3. Troubleshooting and acceptance

- Local curl fails: inspect the process/service, journal, port conflicts and absolute `.venv` path; ensure the command runs on the server, not a client.
- No listener: diagnose startup, dependencies, data and cache permissions first. Opening the firewall cannot fix a stopped application.
- Local access works but remote access fails: that is A's intended isolation; do not change VLAN routing or firewall rules to bypass it.
- Accept only after local pages/APIs work, the listener is loopback-only, remote access to the server LAN IP on port 8000 fails, and no proxy/forwarder exposes it. Inspect health JSON in Section 6 and carry out Section 7's functional checks.

## 4. Deployment B: controlled LAN access

### B1. Identify the real address and firewall policy

After common preparation, run **on the server**:

```bash
ip -4 -brief address
ip route
ss -ltnp | grep ':8000'
```

Ask the network administrator to confirm the client-routable private IP, interface, approved source CIDR and VLAN/access-control lists (ACLs). Do not choose an arbitrary Docker, VPN or loopback address. The examples `192.168.50.10` and `192.168.50.0/24` **must be replaced**.

Review existing policy first. Adding one trusted-CIDR accept rule **does not undo a pre-existing allow-all rule**. Other sources must be denied by default. Check IPv6, upstream ACLs, NAT and other interfaces for bypasses. Do not use an unrestricted `--add-port=8000/tcp` rule or disable the firewall.

This **firewalld-only** fragment is for administrator review, not a universal setup script. `internal` is an example zone: replace it with the zone actually assigned to the LAN interface, with a policy that does not already allow all traffic.

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=internal --list-all
# First confirm unapproved access is denied; separately review broad/conflicting rules
sudo firewall-cmd --permanent --zone=internal \
  --add-rich-rule='rule family="ipv4" source address="192.168.50.0/24" port protocol="tcp" port="8000" accept'
sudo firewall-cmd --reload
sudo firewall-cmd --zone=internal --list-all
```

For nftables, UFW or upstream appliances, have the administrator implement equivalent trusted-source-only access. Do not stack unfamiliar firewall managers. Verify from both approved and unapproved networks.

### B2. Start manually and connect from a client

```bash
cd /opt/skyward
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
.venv/bin/python -m uvicorn app.main:app --host 192.168.50.10 --port 8000
```

Prefer the server's **specific actual LAN IP**. Only after the trusted-subnet firewall is verified may host be changed to `0.0.0.0`. This listens on all IPv4 interfaces but does not change the browser URL.

Run on the server in another terminal, and separately on an authorized client:

```bash
curl -fsS http://192.168.50.10:8000/api/v1/health
curl -fsS http://192.168.50.10:8000/api/v1/config
```

Client browser URL: `http://192.168.50.10:8000/`, substituting the server's real LAN IP; **never `0.0.0.0` or the client's `127.0.0.1`**. When bound to a specific LAN IP, failure of server-side `curl http://127.0.0.1:8000` is not a fault: test the bound address.

### B3. Optional persistent systemd service

`skyward-lan.service` is this section's example service name, not A's `skyward-local.service`. Before installation, replace template IP `192.168.50.10` with the server's actual LAN IP and replace user, group, project and cache paths. Confirm firewall restrictions, stop this section's manual process with Ctrl+C, then run:

```bash
cd /opt/skyward
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward-lan
sudo install -d -o skyward -g skyward -m 0750 /var/cache/skyward-lan/matplotlib /var/cache/skyward-lan/data
sudo -u skyward test -w /var/cache/skyward-lan/matplotlib
sudo -u skyward test -w /var/cache/skyward-lan/data
sudo install -m 0644 deploy/skyward-lan.service /etc/systemd/system/skyward-lan.service
sudo systemctl daemon-reload
sudo systemctl enable --now skyward-lan.service
systemctl status skyward-lan.service --no-pager
journalctl -u skyward-lan.service -n 100 --no-pager
ss -ltnp | grep ':8000'
curl -fsS http://192.168.50.10:8000/api/v1/health
```

### B4. Troubleshooting and acceptance

- Server cannot reach bound IP: check service/journal, `ss`, whether the address exists, cache permissions and port conflicts. `Cannot assign requested address` usually means an unchanged example IP or an interface not yet ready.
- Server works but client fails: check the URL, source CIDR rule, interface zone, routing, inter-VLAN ACLs and upstream isolation. Private addresses do not imply the same VLAN or connectivity; ping success does not prove TCP 8000 is allowed.
- A's loopback listener remains: inspect the running process and unit `ExecStart`. Do not start both A/B on the same port.
- Accept only after server and approved clients reach the actual LAN IP, unapproved networks cannot, no public forwarding exists, and the listener matches the chosen mode. With `0.0.0.0`, explicitly test that other interfaces reject unapproved access.
- Inspect health JSON (Section 6) and functions (Section 7). Record network, time, version and results; HTTP 200 alone is not acceptance.

## 5. Interface, scientific meaning and implemented features

Language (Chinese/English), theme (Auto/Light/Dark) and time zone (Beijing UTC+8 by default, optional UTC) live in browser `localStorage`. Display coordinates can be horizon, J2000 or Galactic; changing the display frame does not change geometry semantics. Auto theme follows the operating system. After upgrading, hard-refresh with Ctrl+Shift+R. Only if settings remain stale, back up local plans and consider clearing this site's localStorage.

### Integrated catalogues and notes (final release review pending)

The following catalogues are now integrated, with this upgrade's snapshot cutoff **2026-09-16**:

| Catalogue | Records | Caveat |
|---|---:|---|
| 2LHAASO | 190 | Preserve original field and coordinate semantics |
| FL16Y | 7224 | Verify units, version and provenance |
| 3FHL | 1556 | Positional uncertainty is not physical extension |
| TeVCat | 361 | Stable catalogue ID `tevcat`; includes candidate groups, **not all confirmed sources** |

These are current integrated data counts, not a claim of deployment, a pushed release or completed full acceptance. Final release review remains pending. The TeVCat cutoff is not a promise of continuous synchronization; see [acquisition notes](../tevcat-acquisition.md). Uploaded CSV catalogues are temporary and must not silently replace released data.

TeVCat `unverified_excerpts` are short unverified excerpts, not measurements. All 361 entries currently have `footprint_known=false` and `planning_radius_deg=null`; even `is_extended=false` does not prove a usable hard boundary. Associations to 2LHAASO contain **0 verified and 186 candidate associations**. These remain candidates: proximity or a 1LHAASO relation does not establish object identity, and TeVCat parameters are not copied into 2LHAASO.

Source notes should identify units, provenance, dataset version/citation, verification state and missing values. Unknown footprint/extension must remain explicitly unknown: a plotted point or default `0` is not a measured physical radius and cannot establish full-footprint containment. Nearby entries in different catalogues are not automatically the same object.

Gaia DR3 provides **candidate calibration stars**, not certified calibration standards. After the base map is ready, the browser independently calls **`GET /api/v1/gaia`** and asynchronously waits for that HTTP response. This is **not a server-side job submission/polling API**; pending is a browser request state, not a returned job ID.

| Parameter / response field | Meaning |
|---|---|
| `target_source_key` | Stable selected-source identity; without a target the query uses current pointing. A query-local row number is not persistent identity |
| `map_kind` | `current` or `local-fov`; a local map requires a target key or complete target coordinates |
| `radius_deg`, `limit`, `max_mag` | Bounded cone, row and magnitude limits; defaults `5°`, `500`, `18`, allowed ranges `0.1–15°`, `1–2000`, `5–22` |
| `sources`, `overlay_svg`, `gaia` | Successful response contains source records, SVG overlay and status metadata, also flattened at top level |
| `count` / `drawn_count` | Returned rows / markers actually rendered in the current projection; these need not match |
| `cached`, `error`, `zero` | Cache hit, query error and successful zero-row result; `zero=true` is not failure |
| `limit`, `truncated` | Requested row cap and whether additional results exist beyond it; a truncated query is not a complete sky census |
| `selection`, `ordering`, `brightest_n` | `bounded_unordered_subset`, `unspecified`, `false`: a bounded unordered subset, not the brightest N stars or a representative sample |
| `query_timeout_seconds` | The independent Gaia network query currently uses a **20-second** finite timeout, not a strict total page/HTTP-response latency guarantee under every condition |

Defaults remain a **5°** radius, at most **500** rows and **G≤18**. The query omits `ORDER BY` to avoid globally sorting dense cones; returned order does not establish brightness ranking, and this subset must not be used to infer completeness or population statistics. Limits remain **2** concurrent queries, **2 MiB** per response and **32** cached queries per process. Timeout or concurrency rejection is an error, not successful zero rows; narrow the query or retry later. The base map loads independently.

A query failure may still use HTTP 200 with top-level `status="error"`, non-null `error` and `zero=false`; error responses may omit `gaia`, `overlay_svg` and `drawn_count`, so clients must handle missing fields. Successful zero rows normally use `status="zero"`, `error=null`. HTTP success alone does not establish Gaia query success; never interpret failure as zero stars. Gaia `source_id` is a string. Current processing only converts the published J2016.0 direction from ICRS to FK5 J2000; **proper motion is not propagated**. The bounded cache is process-local, not promised to survive restart. Local catalogues/basic geometry do not depend on this layer; new Gaia queries cannot be guaranteed offline. See `/openapi.json` for the complete parameter contract.

**1000× zoom magnifies the display only; it does not improve astronomical angular resolution, positional accuracy, underlying data or physical-model resolution.** Preserve uncertainty and provenance at small scales; screen pixels are not measurement precision.

### Status and planning workflow

- GREEN: known centre and nominal extension pass the applicable geometry; YELLOW: centre passes but a known edge fails; RED: centre fails. Do not interpret unknown footprints as fully verified containment.
- Current-sky status uses current pointing/FoV; candidate tracking windows do not approve live equipment pointing. Extension uncertainty and positional errors are not automatically physical extension or colour thresholds.
- Open **Select catalogues** inside the all-sky panel, check the desired catalogues, then choose **Confirm & load**. Checks are drafts until confirmation; Cancel, Escape or clicking outside restores the applied selection. Confirmation refreshes the sky and homepage target search. An empty selection is valid. Result-page layer changes do not replace the calculated target.
- Select a source, or enter a new target's RA, Dec and radius. A blank name yields `TMP JHHMM±DDMM`; temporary targets do not modify 2LHAASO.
- The unzoomed all-sky grid uses 60-degree longitude and 30-degree latitude spacing; local/deep-zoom views adapt the spacing. A solid hollow symbol marks a source; a faint dashed outline is its known nominal extension, not the invisible click target. The Data notes page includes usage, platform scope/roadmap and a single-select introduction for each supported catalogue.
- Choose start/end (at most one day per request). Timezone-free browser inputs use the selected time zone; API timestamps should include `Z` or an explicit offset.
- Defaults: Sun altitude at most `-18°`, Moon separation at least `30°`, target zenith angle `0°–60°`, minimum duration `0 s`. The page requires all five values; API nullability follows OpenAPI.
- Candidate scanning uses one-second samples with refinement of detected pass/fail transitions. Zero minimum duration does not guarantee discovery of every sub-second window.
- A downloadable plan requires a full-footprint interval containing at least two independently checked whole-second instants; endpoints round inward. Plans remain browser-local, not an official server schedule. The download is **`skyward-observing-plan.zip`**, always containing `skyward-observing-plan.txt`. SVG plots are included only for entries whose save-plot option was selected; the ZIP may contain TXT alone.

## 6. Health, IERS and interfaces

Useful routes: `/api/v1` (reference), `/openapi.json`, `GET /api/v1/health`, `GET /api/v1/config`, `GET /api/v1/catalogues`, `GET /api/v1/sources`, `GET /api/v1/sky/current`, `GET /api/v1/gaia`, `POST /api/v1/catalogues/upload`, `POST /api/v1/windows/calculate`. Interactive Swagger/ReDoc are disabled by default; static assets do not require an external CDN.

Read health JSON, not just the HTTP success code:

- `status` is `ok` or `degraded` according to current-time IERS coverage; it does not certify all catalogues, Gaia or scientific results.
- `iers.source_kind="bundled"`: the active table came from bundled/fallback data.
- `iers.source_kind="online_cache"`: the active table came from an online cache, **possibly downloaded previously; this does not prove a successful network request in this run**. Inspect `last_attempt`, `last_success`, `last_error`. These are current-process state and may be null after restart.
- Also inspect `source`, `cache_path`, `first_mjd/last_mjd`, `covers_current_time`, `current_values_are_predicted`, `age_seconds`, `update_due` and `update_interval_days`.

According to `app/astronomy.py`, startup selects a fresh cache or bundled fallback, then starts a bounded background online refresh. A successful download is parsed before atomically replacing cache/active data; failure retains the active table and records an error. The configured seven days controls cache freshness/due information; **it is not a separate timer and does not guarantee weekly refresh in a long-running process**. Astropy's implicit `auto_download=False` does not disable the application's own startup network attempt. Enforce outbound policy for a strictly isolated host. The current request timeout is six seconds, not a hard promise of total elapsed time under every network condition.

Future IERS-A entries may be predictions. Current-time health does not establish coverage of an arbitrary future planning date. Calculations outside active coverage can return HTTP 422. Also check time ordering, the one-day limit and angle parameters when troubleshooting 422.

## 7. Pre-release functional acceptance (execute and record each item)

- Complete the selected A/B connectivity, listener and isolation checks.
- Run the full `.venv/bin/python -m pytest -p no:cacheprovider -q` with Section 0's cache environment, retaining the full report and exit status.
- Check `/`, `/about`, `/api/v1`, language/theme/time-zone changes and source details against API values in a browser.
- Check all four integrated catalogue counts, stable ID `tevcat`, candidate/confirmed groups, units, provenance and unknown footprints; a catalogue listing alone does not verify all data.
- Exercise Gaia pending, successful nonzero, successful zero, cache, failure/offline and recovery states; the base map must not disappear on Gaia failure.
- Check readability at 1000× without implying higher physical resolution; verify known/unknown extent rendering and window interpretation.
- Calculate a window within active IERS coverage and download the plan ZIP where eligible; unpack and check TXT and optional SVG files. HTTP 200 or green colour alone is not scientific acceptance.

## 8. Upgrade, rollback and maintenance

Commands below use **`skyward-local.service` as the concrete example service name**. For B, replace every service command with the actually installed **`skyward-lan.service`**. If still using legacy `lact-window-planner.service`, use that name instead, not an invented `skyward.service`. These are operator instructions, not commands executed for this documentation change.

Record the current commit, active unit and drop-ins, data/provenance hashes, environment versions, cache source and recoverable backups. In a maintenance window, ensure there are no unsaved worktree changes and record the trusted previous commit as `PREVIOUS_GOOD_REF` (placeholder to replace):

```bash
cd /opt/skyward
git status --short
git rev-parse HEAD
systemctl cat skyward-local.service
.venv/bin/python -m pip freeze
# Stop if the worktree is not clean; back up code, data, environment and unit
# Fast-forward only: do not auto-merge or overwrite local changes
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -c 'import sys,numpy,astropy; print(sys.version); assert numpy.__version__=="1.26.4"; assert astropy.__version__=="6.0.1"; print(sys.executable)'
export MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
# Restart only after all checks pass; reviewed unit changes also need daemon-reload
sudo systemctl restart skyward-local.service
systemctl status skyward-local.service --no-pager
curl -fsS http://127.0.0.1:8000/api/v1/health
```

For B, replace the health URL with the server's actual LAN IP. Prefer a separate candidate release directory and rebuilt `.venv`, tested before switching production. Do not leave a live process using dependencies while they are being modified. The in-place example requires administrator-arranged downtime before updates begin; never stop an existing service without authorization.

On failure, stop the upgrade, retain logs and restore backed-up code, data, pinned environment and unit in the maintenance window. With a clean Git worktree and recorded good commit, `git switch --detach PREVIOUS_GOOD_REF` (replace the placeholder) can restore tracked code, but Git **does not restore** untracked data, cache or `.venv`. Do not destroy edits with `git reset --hard` or cleaning commands. Repeat `pip check`, pinned-version assertions and **full pytest** before restarting the actual service. Repeat A/B acceptance and hard-refresh client static assets. Rolling back only code while keeping incompatible data/dependencies is not a complete rollback.

For controlled offline IERS updates, obtain official data, record date/hash, preserve the old file, and verify parsing and coverage:

```bash
cd /opt/skyward
.venv/bin/python - <<'PY'
from astropy.time import Time
from astropy.utils import iers
t = iers.IERS_A.open('data/iers/finals2000A.all')
print('rows:', len(t))
for edge in (0, -1):
    mjd = float(t['MJD'][edge].value)
    print(mjd, Time(mjd, format='mjd').iso)
PY
MPLCONFIGDIR="$PWD/.runtime/matplotlib" SKYWARD_CACHE_DIR="$PWD/.runtime/cache" \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q
```

A fresh cache can still take precedence after replacing bundled data. After restart inspect actual `source/source_kind`; back up and manage cache changes under the change procedure instead of assuming file replacement switched the active table. Preserve units, provenance, grouping, missing-value semantics and test records for every catalogue update.
