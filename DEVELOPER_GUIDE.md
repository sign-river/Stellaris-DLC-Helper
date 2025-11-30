## Stellaris DLC Helper - Developer Guide

This consolidated developer guide combines packaging, deployment, update, and multi-source logic documentation for maintainers and contributors.

---

# Table of Contents
- Overview
- Architecture & Components
- Multi-source download logic
- Packaging & Build
- Deployment
- Update system
- Testing & Tools
- Cleanup & Maintenance
- Contributing

---

## Overview
This guide contains developer-oriented documentation: packaging, deployment, multi-source logic, update flow, and testing scripts. Use this guide to onboard new developers and keep a single place for technical maintenance.

## Architecture & Components
Contents excerpted and consolidated from `MULTI_SOURCE_README.md` and `DOWNLOAD_LOGIC_DETAIL.md`.

### Core Components
- SourceManager: Manages sources, URL generation, and source selection
- DLCManager: Manages DLC index fetching and url mapping
- Downloader: Handles file download with resume and verification
- Installer: Extracts and installs DLC into the game folder
- GUI: MainWindow and UI components

### Multi-Source Logic
The project supports 4 download sources: R2 (Cloudflare), domestic cloud, GitHub (releases), Gitee (releases). The system builds a per-DLC URL map and chooses a source using speed tests and thresholds.

Key behaviors:
- Test URLs are either explicit via `config.json` or use stable defaults per source.
- `get_best_download_source()` runs full tests using `measure_speed()` with configurable thresholds.
- `find_first_source_above()` runs quick/lightweight tests (lower max_seconds & max_bytes) to detect fast sources without impacting current downloads.
- `DLCDownloader` uses fallback URLs and supports resume and SHA256 verification.

## Packaging & Build
Use `build.py` for automated packaging (virtualenv creation and PyInstaller run). See `PACKAGING.md` for manual steps and troubleshooting.

## Deployment
Servers and file layout details are consolidated here: R2 uses a bucket, domestic_cloud serves `index.json`, Github/Gitee use release assets. See `DEPLOYMENT_GUIDE.md` for deployment commands and naming conventions.

## Update System
`updater.py` and `update_dialog.py` provide auto update and rollback; configuration format and version.json described in `UPDATE_README.md`.

## Testing & Tools
Useful scripts are located under `tools/`:
- `tools/connectivity_test.py` - checks connectivity to each source
- `tools/show_test_candidates.py` - prints test URLs for configured sources
- `tools/test_get_best.py` - runs speed selection logic
- `tools/dump_url_map.py` - outputs the generated per-DLC url map cache

### Quick developers tasks
- Run `python tools/test_get_best.py` to validate speed selection
- Run `python tools/connectivity_test.py` to validate server availability

## Cleanup & Maintenance
- Build artifacts: `build/` can be removed or archived
- Cache: `Stellaris_DLC_Cache/dlc/` and log files can be removed to reclaim space
- Use `tools/` scripts for diagnostics and to re-generate `dlc_urls.json`

## Contributing
- PRs must include tests or documentation updates
- Feature additions require an update to `DEVELOPER_GUIDE.md`

---

This consolidated guide replaces the multiple fragmented MD files. The originals are available in `docs/legacy/` for history.

---

## Detailed: Packaging (from PACKAGING.md)

```
`PACKAGING.md` content: see documentation file (packaging, venv, pyinstaller steps)
```

## Detailed: Multi-Source and Download Logic
The multi-source and download logic is derived from `MULTI_SOURCE_README.md` and `DOWNLOAD_LOGIC_DETAIL.md`.

Key highlights:
- Source types and URL mapping
- How `get_best_download_source` and `find_first_source_above` work
- Speed testing thresholds and parameters
- Fault tolerance, resume, and SHA verification

## Detailed: Deployment (from DEPLOYMENT_GUIDE.md)

Deployment steps and directory expectations for R2, domestic_cloud, GitHub, and Gitee.

## Detailed: Update / Auto-update (from UPDATE_README.md)

Update server layout, `version.json` format, and update steps.

## Release Notes (v1.0.0)

See `RELEASE_NOTES.md` for full history and change log.

