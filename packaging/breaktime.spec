# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Break-Time.

MediaPipe ships model/data files (face landmark models etc.) that PyInstaller's default
import analysis does not pick up automatically -- collect_data_files handles that. Built
as a onedir bundle (not onefile): onefile's self-extract-on-launch startup cost is a poor
fit for a background tray app that should appear near-instantly, versus a CLI tool where
that cost matters less.

Run from the repo root: `pyinstaller packaging/breaktime.spec --noconfirm`
Relative paths below are resolved relative to this spec file's own directory.
"""

from PyInstaller.utils.hooks import collect_data_files

mediapipe_datas = collect_data_files("mediapipe")
# Our own downloaded model (scripts/download_model.py) -- not part of the mediapipe
# package's own data, so it needs to be listed explicitly.
face_model_datas = [
    ("../src/breaktime/vision/models/face_landmarker.task", "breaktime/vision/models")
]

a = Analysis(
    ["entrypoint.py"],
    pathex=["../src"],
    binaries=[],
    datas=mediapipe_datas + face_model_datas,
    hiddenimports=["win11toast", "pystray._win32"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="breaktime",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="breaktime",
)
