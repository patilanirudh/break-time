"""System tray icon: shows current state at a glance, exposes quick settings/stats."""

from __future__ import annotations

from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from breaktime.core.types import SessionPhase

_COLORS: dict[SessionPhase, tuple[int, int, int]] = {
    SessionPhase.ACTIVE: (46, 160, 67),
    SessionPhase.AWAY: (140, 140, 140),
    SessionPhase.BREAK_PENDING: (219, 154, 4),
    SessionPhase.BREAK_VERIFYING: (219, 154, 4),
    SessionPhase.BREAK_COMPLETE: (46, 160, 67),
}
_PAUSED_COLOR: tuple[int, int, int] = (100, 100, 220)

_INTERVAL_PRESETS_MINUTES = (15, 20, 30, 45, 60)


def _make_icon_image(color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return image


class TrayApp:
    """Owns the pystray Icon. Call `update_phase` from the tracking loop to reflect state."""

    def __init__(
        self,
        *,
        on_open_stats: Callable[[], None],
        on_toggle_auto_start: Callable[[bool], None],
        on_toggle_paused: Callable[[bool], None],
        on_set_break_interval_minutes: Callable[[int], None],
        on_request_custom_interval: Callable[[], None],
        on_quit: Callable[[], None],
        auto_start_enabled: bool,
        break_interval_minutes: int,
    ) -> None:
        self._on_open_stats = on_open_stats
        self._on_toggle_auto_start = on_toggle_auto_start
        self._on_toggle_paused = on_toggle_paused
        self._on_set_break_interval_minutes = on_set_break_interval_minutes
        self._on_request_custom_interval = on_request_custom_interval
        self._on_quit = on_quit
        self._auto_start_enabled = auto_start_enabled
        self._paused = False
        self._break_interval_minutes = break_interval_minutes
        self._last_phase = SessionPhase.ACTIVE

        self.icon = pystray.Icon(
            "breaktime",
            icon=_make_icon_image(_COLORS[SessionPhase.ACTIVE]),
            title="Break-Time",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        interval_items = [
            pystray.MenuItem(
                f"{minutes} minutes",
                lambda _item, m=minutes: self._on_set_break_interval_minutes(m),
                checked=lambda _item, m=minutes: self._break_interval_minutes == m,
                radio=True,
            )
            for minutes in _INTERVAL_PRESETS_MINUTES
        ]
        interval_items.append(
            pystray.MenuItem(
                "Custom...",
                lambda: self._on_request_custom_interval(),
                checked=lambda _item: self._break_interval_minutes not in _INTERVAL_PRESETS_MINUTES,
                radio=True,
            )
        )

        return pystray.Menu(
            pystray.MenuItem("Today's stats", lambda: self._on_open_stats()),
            pystray.MenuItem("Break interval", pystray.Menu(*interval_items)),
            pystray.MenuItem(
                "Pause Break-Time",
                lambda: self._on_toggle_paused(not self._paused),
                checked=lambda _item: self._paused,
            ),
            pystray.MenuItem(
                "Start with Windows",
                lambda: self._on_toggle_auto_start(not self._auto_start_enabled),
                checked=lambda _item: self._auto_start_enabled,
            ),
            pystray.MenuItem("Quit", lambda: self._on_quit()),
        )

    def set_auto_start_state(self, enabled: bool) -> None:
        self._auto_start_enabled = enabled
        self.icon.update_menu()

    def set_paused_state(self, paused: bool) -> None:
        self._paused = paused
        self.icon.update_menu()
        self.icon.icon = _make_icon_image(_PAUSED_COLOR if paused else _COLORS[self._last_phase])

    def set_break_interval_minutes(self, minutes: int) -> None:
        self._break_interval_minutes = minutes
        self.icon.update_menu()

    def update_phase(self, phase: SessionPhase) -> None:
        self._last_phase = phase
        if not self._paused:
            self.icon.icon = _make_icon_image(_COLORS[phase])

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()
