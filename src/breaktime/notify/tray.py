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
        on_quit: Callable[[], None],
        auto_start_enabled: bool,
    ) -> None:
        self._on_open_stats = on_open_stats
        self._on_toggle_auto_start = on_toggle_auto_start
        self._on_quit = on_quit
        self._auto_start_enabled = auto_start_enabled

        self.icon = pystray.Icon(
            "breaktime",
            icon=_make_icon_image(_COLORS[SessionPhase.ACTIVE]),
            title="Break-Time",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Today's stats", lambda: self._on_open_stats()),
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

    def update_phase(self, phase: SessionPhase) -> None:
        self.icon.icon = _make_icon_image(_COLORS[phase])

    def run(self) -> None:
        self.icon.run()

    def stop(self) -> None:
        self.icon.stop()
