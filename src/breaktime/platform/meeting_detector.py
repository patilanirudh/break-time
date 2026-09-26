"""Best-effort detection of common desktop video-conferencing apps.

Used to suppress the break-reminder popup while a call is likely in progress -- a toast
interrupting a video call, or worse a proctored exam, is exactly the kind of disruptive
experience this project should avoid causing. This is inherently a heuristic: a
browser-based meeting running inside a generic browser process can't be distinguished
this way, and there's no way to enumerate every exam-proctoring product that exists. The
manual "Pause Break-Time" tray toggle exists precisely for what this list can't catch.

Only process *names* are inspected here, nothing else (no window titles, no network
activity, no camera/mic content) -- consistent with the project's privacy stance.
"""

from __future__ import annotations

import psutil

_MEETING_PROCESS_NAMES = frozenset(
    {
        "zoom.exe",
        "teams.exe",
        "ms-teams.exe",
        "webexmta.exe",
        "webex.exe",
        "skype.exe",
        "discord.exe",
        "slack.exe",
        "gotomeeting.exe",
        "ringcentral.exe",
    }
)


def is_meeting_app_running() -> bool:
    for process in psutil.process_iter(["name"]):
        name = (process.info.get("name") or "").lower()
        if name in _MEETING_PROCESS_NAMES:
            return True
    return False
