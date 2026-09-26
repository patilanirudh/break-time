# Break-Time

Break-Time is a privacy-first desktop app that watches for digital eye strain using your
webcam and nudges you to take a break — but unlike a plain timer, it **verifies you
actually looked away** before marking the break complete, instead of trusting a dismissible
popup.

## Why this exists

Most break reminders are dumb timers: they fire on a schedule whether or not you're even at
your desk, and a single click makes them go away whether or not you took a real break. They
also tend to interrupt you mid-meeting or mid-exam with no awareness of what else is going
on. Break-Time instead:

- Detects real screen-facing time and blink-rate fatigue using on-device computer vision
  (OpenCV + MediaPipe), personalized to your own calibrated head pose and eye position —
  not a fixed universal angle
- Only marks a break "done" once it observes you actually look away from the screen for the
  required duration
- Stays quiet during video calls (detects common meeting apps) and has a one-click "Pause"
  for exams or proctoring software
- Lets you set your own break interval, not just one hardcoded number
- Runs entirely locally — see [Privacy](#privacy) below

## Features

- **Verified breaks** — closed-loop confirmation via vision, not a button click
- **Personalized calibration** — a short one-time setup (look at the center, then each
  screen edge) grounds "on screen" in your actual screen/seating geometry and your own eye
  shape, instead of a guessed universal threshold
- **Fatigue detection** — flags a break when your blink rate drops meaningfully below your
  own calibrated baseline, not just on a timer
- **Meeting/exam awareness** — suppresses the break popup while a known video-conferencing
  app is running (still tracks quietly in the background); a manual "Pause Break-Time" tray
  toggle fully releases the camera for exams or proctoring software
- **Customizable break interval** — presets (15/20/30/45/60 min) or a custom value, from the
  tray menu
- **Local stats** — today's verified break count and current streak, from the tray menu
- **Auto-start at login** — on by default, one click to disable

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
- Meeting-app detection only ever inspects process *names* (e.g. is `zoom.exe` running) —
  never window content, network traffic, or camera/mic data from other apps.
- Auto-start at login is on by default (so you don't have to remember to launch it) but is a
  one-click toggle to disable in the tray settings.

## Known limitations

Documented honestly rather than hidden:

- **A brief, purely eyes-only glance (head held perfectly still) at an extreme angle isn't
  always caught.** Live testing found the underlying eye-position signal often doesn't move
  enough to register in that specific scenario — real, sustained head+eye redirects (the
  natural way people actually look away) are detected reliably. Closing this gap fully would
  need a heavier gaze-estimation technique (multi-point regression, higher-resolution eye
  crops), which is a bigger undertaking than the current lightweight approach.
- Windows only for now.

## Installing (end users)

Download the latest `BreakTimeSetup-x.y.z.exe` from the
[Releases](https://github.com/patilanirudh/break-time/releases) page and run it. No Python
required.

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

The first run walks through calibration: look at your screen normally for about a minute
and a half, then briefly at each screen edge when prompted (via toast notification). This
personalizes every threshold to your own camera angle and eye shape — see
[Known limitations](#known-limitations) and the code comments in `vision/calibration.py`
and `vision/gaze.py` for why a one-size-fits-all threshold didn't work.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full developer workflow, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations.

### Verifying detection is working

Since no camera frame is ever saved (see Privacy above), there's no file to inspect to
check detection quality. Instead, run:

```bash
breaktime --debug-preview
```

This opens a live local window showing the camera feed with the current EAR, blink
threshold, calibrated on-screen ranges, gaze/head-pose readings, and the combined
"looking at screen" judgment overlaid in real time, so you can watch the numbers respond
as you blink or look away. Nothing in this window is ever saved or sent anywhere; press
`q` to close it. This is a separate mode from the normal background tray app, which never
displays camera output at all.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
