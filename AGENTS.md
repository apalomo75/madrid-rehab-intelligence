# Repository Guidelines

## Project Structure & Module Organization

The Python application is under `src/madrid_rehab/`, unittest tests under `tests/`, and documentation under `docs/`. Local originals and generated Parquet live under ignored `data/raw/` and `data/processed/`. The existing `.agents/`, `.codex/`, `.aws/`, and `.git/` directories are environment-managed; do not use them for application code or modify them as part of routine contributions.

When adding the initial implementation, organize application code under `src/`, automated tests under `tests/`, and project documentation under `docs/`. Introduce data or asset directories only when needed, and document their purpose. Keep generated outputs separate from source files.

## Build, Test, and Development Commands

Install: `.venv/bin/python -m pip install -r requirements.lock`.
Test: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`.
Lint: `.venv/bin/ruff check src tests`.
Format new ingestion code: `.venv/bin/ruff format src/madrid_rehab/ingest.py tests/test_ingest.py`.
Municipal ingestion: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.ingest`.
Offline replay: add `--offline --output-dir data/processed/session_1_replay`.
Session 2 (offline): `PYTHONPATH=src .venv/bin/python -m madrid_rehab.session2`.
Official boundaries (one capture): `PYTHONPATH=src .venv/bin/python -m madrid_rehab.districts`.
Session 3 interaction: `PLAYWRIGHT_BROWSERS_PATH=/tmp/madrid-rehab-browser PYTHONPATH=src .venv/bin/python tests/browser_session3.py` (local server required).
Session 3 preparation benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_session3.py`.
Session 3 offline viewer: prefix the local app command with `MADRID_REHAB_OFFLINE=1`.
Session 3 reports/screenshots go under `reports/session_3/`; see `docs/visor.md` and `docs/componente_cartografico.md`. Browser permission failures must be reported as blocked, never as successful visual validation.
Local app: `PYTHONPATH=src .venv/bin/python -m streamlit run src/madrid_rehab/app.py --server.address 127.0.0.1 --server.port 8512`.
See README.md, docs/ingesta.md and docs/integracion_ceee_catastro.md for commands and data contracts.
Never overwrite session 1 or original data. Session 2 outputs go under `data/processed/session_2/`; use a new directory for replay. Do not promote parcel matches to physical-building confirmation. The map must keep certificate scope and all matching levels visible. No automatic Git commits or internet publication are authorized.

When introducing a toolchain, commit its dependency manifest and applicable lockfile. Document exact installation, development, test, and build commands in `README.md`, and update this guide to match.

## Coding Style & Naming Conventions

Use Python 3.11+, four spaces, Ruff lint rules configured in pyproject.toml, and Ruff format for new modules. Follow the conventions of the language selected for the first implementation, use consistent indentation, and configure an appropriate formatter and linter alongside that implementation.

Use descriptive module and function names. Keep modules focused, and avoid mixing generated files with maintained code.

## Testing Guidelines

Use standard-library unittest; no coverage threshold is configured. Add tests with new behavior and regression tests for bug fixes. Mirror source organization under `tests/` and follow the chosen framework's discovery conventions. Document how to run the complete suite and individual tests.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so no existing commit convention can be verified. Use concise, imperative commit subjects, such as `Add configuration loader`.

Pull requests should explain the change, its purpose, and validation performed. Link relevant issues and include screenshots for visible interface changes. Explicitly identify checks that could not be run.

## Security & Configuration

Never commit credentials, local environment files, or private datasets. Provide placeholder configuration examples and ignore local secrets and generated artifacts when introducing project configuration.

Session 4/5 canonical imports: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.events inspection --input /path/official_canonical.csv --output-dir data/processed/session_4_import_01` (use `grant` for session 5). No official event records have been imported yet; see source audits before importing.
Session 6 offline analysis: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.analytics`; use a new `--output-dir` for replay. Tests: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_sessions456.py -v`. Viewer profile directory override: `MADRID_REHAB_SESSION6_DIR`. Global IPR is unavailable; sensitivity scores are an audit artifact, not building diagnoses.
Analytical v2 default output/viewer: `data/processed/session_6_audited/`; preserve v1 and use a new output directory for each replay. Deepening tests: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_analysis_deepening.py -v`. Analysis benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_analysis.py`. Optional `--inspections-dir`/`--grants-dir` require reviewed canonical event snapshots with matching CP hashes; never use synthetic data outside tests. See `docs/auditoria_analitica_chamberi.md`.

Session 7 municipal pipeline (offline): `PYTHONPATH=src .venv/bin/python -m madrid_rehab.city_pipeline --city madrid --district all`, default output `data/processed/session_7_final/`. Use a new `--output-dir` for replay; `--district chamberi` or official codes generate selected detail while preserving global identity checks. The normal app entry is municipal; `MADRID_REHAB_PILOT=1` preserves the historical pilot. Municipal override: `MADRID_REHAB_SESSION7_DIR`. Benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_session7.py`. Tests: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_city_*.py' -v`. Never treat grid cells as official neighborhoods or sum distinct-certificate memberships across districts without reconciliation. See `docs/sesion_7_expansion_madrid.md` and `docs/calidad_sesion_7.md`.

Session 7.1 navigation benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_session71.py`; tests `test_session71_navigation.py`. Session 8 bounded acquisition: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.official_sources urban_2019 --raw-dir data/raw/session_8_capture_03`; always use a new directory after a failed attempt or for updates. No new official event records were acquired; urban inspections are not ITE/IEE. Source adapter tests: `test_public_sources.py`. Session 9 scenario D audit: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.integration_audit --output-dir reports/session_9/replay_02`; use a new output. See docs/sesion_8_fuentes_oficiales.md and docs/sesion_9_integracion.md. Do not turn normalized_requires_review adapters or unknown source coverage into public events or zero occurrence rates.

Session 10 administrative import: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative --output-dir data/processed/administrative_events/replay_new --report-dir reports/session_10/replay_new`. Current viewer snapshot: `data/processed/administrative_events/session_10_final_01/`; override `MADRID_REHAB_ADMIN_DIR` requires the same municipal CP hash. New output directory for every replay; originals are copied once by SHA-256 under `data/raw/administrative/`. PDF extraction requires system `pdftotext` (Poppler); XLSX uses inert XML, no openpyxl dependency or formula execution. Tests: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_administrative.py -v`. Benchmark: `PYTHONPATH=src .venv/bin/python tests/benchmark_administrative.py --output reports/session_10/benchmark_new.json`. Profiles/audit: `PYTHONPATH=src .venv/bin/python -m madrid_rehab.administrative_audit --output-dir data/processed/administrative_profiles/replay_new --report-dir reports/session_10/audit_new`. ITE/IEE pending obligations are not inspection outcomes; order numbering is a publication ordinal, not a globally unique case ID. No individual grant awards are available in the provided files. See docs/sesion_10_integracion_administrativa.md. No commits or push.
