# Repository Guidelines

## Project Structure & Module Organization

This repository currently has no application source, tests, assets, or dependency manifests. The existing `.agents/`, `.codex/`, `.aws/`, and `.git/` directories are environment-managed; do not use them for application code or modify them as part of routine contributions.

When adding the initial implementation, organize application code under `src/`, automated tests under `tests/`, and project documentation under `docs/`. Introduce data or asset directories only when needed, and document their purpose. Keep generated outputs separate from source files.

## Build, Test, and Development Commands

No build, test, lint, or local development commands are configured yet. Do not assume that `npm test`, `pytest`, or `make build` works.

When introducing a toolchain, commit its dependency manifest and applicable lockfile. Document exact installation, development, test, and build commands in `README.md`, and update this guide to match.

## Coding Style & Naming Conventions

No language-specific style or formatter has been established. Follow the conventions of the language selected for the first implementation, use consistent indentation, and configure an appropriate formatter and linter alongside that implementation.

Use descriptive module and function names. Keep modules focused, and avoid mixing generated files with maintained code.

## Testing Guidelines

No testing framework or coverage threshold is configured. Add tests with new behavior and regression tests for bug fixes. Mirror source organization under `tests/` and follow the chosen framework's discovery conventions. Document how to run the complete suite and individual tests.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so no existing commit convention can be verified. Use concise, imperative commit subjects, such as `Add configuration loader`.

Pull requests should explain the change, its purpose, and validation performed. Link relevant issues and include screenshots for visible interface changes. Explicitly identify checks that could not be run.

## Security & Configuration

Never commit credentials, local environment files, or private datasets. Provide placeholder configuration examples and ignore local secrets and generated artifacts when introducing project configuration.
