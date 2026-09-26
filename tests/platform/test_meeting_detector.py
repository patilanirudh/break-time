from breaktime.platform import meeting_detector


class _FakeProcess:
    def __init__(self, name: str) -> None:
        self.info = {"name": name}


def test_returns_false_when_no_meeting_process_running(monkeypatch):
    monkeypatch.setattr(
        meeting_detector.psutil,
        "process_iter",
        lambda _attrs: iter([_FakeProcess("explorer.exe"), _FakeProcess("chrome.exe")]),
    )
    assert meeting_detector.is_meeting_app_running() is False


def test_returns_true_when_a_known_meeting_process_is_running(monkeypatch):
    monkeypatch.setattr(
        meeting_detector.psutil,
        "process_iter",
        lambda _attrs: iter([_FakeProcess("explorer.exe"), _FakeProcess("Zoom.exe")]),
    )
    assert meeting_detector.is_meeting_app_running() is True


def test_matching_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        meeting_detector.psutil,
        "process_iter",
        lambda _attrs: iter([_FakeProcess("TEAMS.EXE")]),
    )
    assert meeting_detector.is_meeting_app_running() is True
