# Roadmap

## Phase 0 — Repo & open-source scaffolding
Licensing, contributor docs, CI, issue templates. Foundation only, no app logic.

## Phase 1 — Core detection engine
On-device vision pipeline: webcam capture, blink/EAR detection, gaze + head-pose estimation,
per-user calibration, the continuous-screen-time state machine, and the verified-break
closed loop (the feature that differentiates this from a dismissible-popup timer).

## Phase 2 — App shell & UX
System tray icon, native Windows toast notifications, local SQLite stats storage.

## Phase 3 — Tests & packaging
Unit tests for everything that doesn't require a real camera (EAR math, state machine,
calibration), lint/type-check/security CI, editable-install packaging for contributors.

## Phase 4 — Open-source launch readiness
Real README content and screenshots, labeled "good first issue" tickets, first tagged
release.

## Phase 5 — End-user distribution
Standalone Windows installer (PyInstaller + Inno Setup) published via GitHub Releases,
auto-start at login with an opt-out toggle, manual updates for v1 (no auto-updater, no
background network calls).

---

## Explicitly deferred (not built yet, tracked here so intent is clear)

- **Mobile app.** Market research pointed at a mobile-first product long-term (most digital
  eye strain and doomscrolling happens on the phone, not the desktop), but the desktop
  prototype exists first to validate the detection + verified-break logic cheaply before
  committing to React Native/Flutter + on-device ML Kit/MediaPipe Tasks. The calibration,
  EAR, and verified-break *logic* is designed to port, not the Python code directly.
- **Mood/emotional-state correlation.** V1 ships only a small, clearly-labeled
  *experimental* facial-expression hint — not a diagnostic claim. Full correlation of eye
  fatigue with emotional/stress signal (the biggest long-term differentiator identified in
  research) is a later phase once the eye-detection core is validated with real usage.
- **Web dashboard.** Deliberately excluded from v1 — fully native (tray + toast only), no
  local web server, nothing listening on any port. May be revisited once there's real usage
  data to justify a richer stats view.
- **Auto-updates, cloud sync, accounts, or any team/aggregate reporting.** This project is
  local-only and single-user by design; anything requiring a server is out of scope unless
  explicitly revisited.
