"""Windows auto-start registration via the per-user Registry Run key.

Uses HKEY_CURRENT_USER, not HKEY_LOCAL_MACHINE -- no admin rights required, and it only
affects the current user, consistent with this being a single-user local app.
"""

from __future__ import annotations

import sys
import winreg

from breaktime.core.logging import get_logger, log_event

_logger = get_logger("platform.autostart")
_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "BreakTime"


def set_enabled(enabled: bool) -> None:
    """Add or remove the startup entry.

    `sys.executable` is the packaged breaktime.exe when running from the installer
    (the real end-user path); when running from source it points at python.exe instead,
    which is fine for development but not a correct standalone launch command -- auto-
    start is primarily meant for the installed app.
    """
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            command = f'"{sys.executable}"'
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)
            log_event(_logger, "autostart_enabled")
        else:
            try:
                winreg.DeleteValue(key, _VALUE_NAME)
                log_event(_logger, "autostart_disabled")
            except FileNotFoundError:
                pass


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
