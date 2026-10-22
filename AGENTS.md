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
