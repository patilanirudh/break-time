# Packaging

Builds the end-user Windows installer. This is exercised automatically by
`.github/workflows/release.yml` on every version tag push; the steps below are for
building and sanity-checking it locally.

```bash
pip install -e .
pip install pyinstaller
python scripts/download_model.py
pyinstaller packaging/breaktime.spec --noconfirm
# produces dist/breaktime/ (onedir bundle) at the repo root

# Requires Inno Setup (https://jrsoftware.org/isinfo.php) installed locally, or
# `choco install innosetup` on the CI runner.
set BREAKTIME_VERSION=0.1.0
iscc packaging/installer.iss
# produces packaging/dist/BreakTimeSetup-0.1.0.exe
```

Note: this packaging config has not yet been exercised end-to-end against a real built
app (that requires the app itself to be runnable first, camera and all). Treat the first
real build as a verification step, not an assumption baked in here — MediaPipe's data-file
bundling in particular (`collect_data_files("mediapipe")` in `breaktime.spec`) is the part
most likely to need adjustment once actually run.
