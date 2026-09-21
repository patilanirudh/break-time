# Break-Time

Break-Time is a privacy-first desktop app that watches for digital eye strain using your
webcam and nudges you to take a break — but unlike a plain timer, it **verifies you
actually looked away** before marking the break complete, instead of trusting a dismissible
popup.

## Why this exists

Most break reminders are dumb timers: they fire on a schedule whether or not you're even at
your desk, and a single click makes them go away whether or not you took a real break.
Break-Time instead:

- Detects real screen-facing time and blink-rate fatigue using on-device computer vision
  (OpenCV + MediaPipe), personalized to your own calibrated baseline
- Only marks a break "done" once it observes you actually look away from the screen for the
  required duration
- Runs entirely locally — see [Privacy](#privacy) below

## Privacy

This is the core design constraint of the whole project, not an afterthought:

- Camera frames are analyzed in memory and discarded immediately. **No image or video frame
  is ever written to disk, logged, or sent anywhere.**
- All data (blink-rate history, break events, streaks) stays in a local SQLite database on
  your machine. Nothing is uploaded.
- The running app makes **no network calls at all**. The one exception in the whole
  project is `scripts/download_model.py`, a one-time setup/build step (run by a
  contributor once, or by CI before packaging a release) that fetches the public
  MediaPipe face-detection model file and verifies its checksum. The shipped app only
  ever reads that model from local disk. Crash reporting exists but is **off by default**
  and strictly opt-in — see `SECURITY.md`.
- Auto-start at login is on by default (so you don't have to remember to launch it) but is a
  one-click toggle to disable in the tray settings.

## Status

Early development — see [docs/ROADMAP.md](docs/ROADMAP.md) for what's built, what's in
progress, and what's explicitly deferred (including a future mobile app).

## Installing (end users)

Download the latest `BreakTimeSetup-x.y.z.exe` from the
[Releases](https://github.com/) page and run it. No Python required. Windows only for now.

## Running from source (contributors)

```bash
git clone <repo-url>
cd break-time
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
python scripts/download_model.py   # one-time fetch of the local face detection model
breaktime
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full developer workflow, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations.

### Verifying detection is working

Since no camera frame is ever saved (see Privacy above), there's no file to inspect to
check detection quality. Instead, run:

```bash
breaktime --debug-preview
```

This opens a live local window showing the camera feed with the current EAR, blink
threshold, gaze-on-screen status, and head pose overlaid in real time, so you can watch
the numbers respond as you blink or look away. Nothing in this window is ever saved or
sent anywhere; press `q` to close it. This is a separate mode from the normal background
tray app, which never displays camera output at all.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
