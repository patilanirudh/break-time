# Security Policy

## Reporting a vulnerability

Because this application accesses a webcam, we take security and privacy reports
seriously. If you find a vulnerability — especially anything that could cause camera data
to be written to disk, logged, or transmitted off the device — please **do not open a
public GitHub issue**. Instead, use GitHub's private "Report a vulnerability" flow on this
repository's Security tab, or contact a maintainer directly.

Please include:

- A description of the issue and its potential impact
- Steps to reproduce
- Affected version/commit

We'll acknowledge reports as quickly as we can and credit reporters in the fix release
notes unless you'd prefer to stay anonymous.

## Privacy-related guarantees this project makes

- Camera frames are processed in memory only and are never written to disk, logged, or
  transmitted. Any bug that violates this is treated as a security issue, not a regular bug.
- Crash/error reporting is **disabled by default** and only ever activates if a user
  explicitly opts in from settings. Even when enabled, it never includes camera frames —
  only stack traces and non-identifying app/OS metadata.
- All stored data (SQLite database under `~/.breaktime/`) contains only derived numeric
  metrics (blink rate, timestamps, break durations) — never raw images.
- No telemetry, analytics, or background network calls exist in v1. The sole exception is
  `scripts/download_model.py`, a one-time setup/build step (never run by the app itself)
  that fetches the public MediaPipe face-detection model and verifies its SHA-256 before
  use; the shipped, running app only ever reads that model from local disk.

## Supported versions

Only the latest released version is supported with security fixes during this early-stage
phase.
