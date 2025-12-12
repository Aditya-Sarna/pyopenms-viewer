# Repository Guidelines

## Project Structure & Module Organization

- Core CLI and UI logic live in `pyopenms_viewer.py` (entry point `pyopenms-viewer` → `pyopenms_viewer:main`).
- Keep related functionality close together in `pyopenms_viewer.py` unless there is a clear need to extract a new module.
- When splitting code, create focused modules at the project root and mirror their names in `tests/` (for example, `tests/test_pyopenms_viewer.py`).

## Build, Test, and Development Commands

- Install dev dependencies (recommended): `uv sync --extra dev`  
  or with pip: `pip install -e ".[dev]"`.
- Run the viewer locally: `uv run pyopenms-viewer sample.mzML`.
- Run tests: `uv run pytest`.
- Lint and format: `uv run ruff check .` and `uv run ruff format .`.

## Coding Style & Naming Conventions

- Python 3.10+, 4-space indentation; let `ruff` be the source of truth (see `pyproject.toml`), with line length 120.
- Functions and variables use `lower_snake_case`; classes use `PascalCase`; constants use `UPPER_SNAKE_CASE`.
- Prefer explicit, descriptive names and type hints for new or modified public functions.
- Keep imports ordered and grouped; rely on `ruff` autofixes where possible instead of manual style tweaks.

## Testing Guidelines

- Use `pytest` with tests in `tests/` named `test_*.py`.
- Every new feature or bug fix should be covered by at least one test where practical.
- For visualization-heavy code, focus tests on data processing and helpers rather than rendered pixels.

## Commit & Pull Request Guidelines

- Write concise, imperative commit messages (for example, `Add peak annotation to spectra`, `Fix spectrum zoom for ID selection`).
- Before opening a PR, ensure `uv run pytest` and `uv run ruff check .` both pass.
- PRs should include a short summary, linked issues (for example, `Fixes #123`), and screenshots or GIFs for UI or interaction changes.

## Agent-Specific Notes

- Keep changes minimal and focused, preserving existing structure and naming.
- Prefer extending existing functions and patterns in `pyopenms_viewer.py` before introducing new modules.
- Avoid adding new dependencies unless clearly justified and explained in the PR description.
