# Contributing to Break-Time

Thanks for considering contributing. This project is small and early-stage, so the process
is intentionally lightweight.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
python scripts/download_model.py
```

This installs the app in editable mode plus the dev tools (ruff, mypy, pytest,
pre-commit, pip-audit), wires up pre-commit hooks so lint/format/type checks run
automatically on `git commit`, and fetches the local face-detection model that
`vision/detection.py` needs to actually run (not required just to run `pytest` --
the unit tests use synthetic fixtures, not a real model or camera).

## Before opening a PR

```bash
ruff check .
ruff format .
mypy src
pytest
pip-audit
```

All of these also run in CI on every PR — running them locally first saves a review
round-trip.

## Code organization

The app is structured as a pipeline of isolated, typed stages under `src/breaktime/`:
`vision/` (capture → detection → calibration → verified break) feeds `state/` (the
session/fatigue state machine), which drives `notify/` (tray + toast) and `storage/`
(local SQLite). Each stage takes and returns the shared dataclasses defined in
`core/types.py`, which is what makes each stage independently testable — see `tests/` for
the pattern (synthetic `DetectionResult` fixtures, no real camera needed).

## Privacy is a hard constraint, not a preference

Any change that would cause a camera frame to be written to disk, logged, or transmitted
anywhere will not be merged, regardless of the feature it enables. If you're unsure whether
a change crosses this line, ask in the PR description before writing the code.

## Commit style

Plain, descriptive commit messages explaining *why* a change was made. No fixed format
required.

## Reporting bugs / requesting features

Use the GitHub issue templates. For anything touching security or privacy, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.
