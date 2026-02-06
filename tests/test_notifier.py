import time
from unittest.mock import patch

from core.notifier import notify


class TestNotify:
    @patch("core.notifier.subprocess.run")
    def test_calls_osascript(self, mock_run):
        notify("Title", "Message")
        time.sleep(0.3)  # Wait for daemon thread
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "osascript"
        assert cmd[1] == "-e"
        assert "Title" in cmd[2]
        assert "Message" in cmd[2]

    @patch("core.notifier.subprocess.run")
    def test_escapes_quotes(self, mock_run):
        notify('Ti"tle', 'Mes"sage')
        time.sleep(0.3)
        cmd = mock_run.call_args[0][0]
        assert 'Ti\\"tle' in cmd[2]
        assert 'Mes\\"sage' in cmd[2]

    @patch("core.notifier.subprocess.run", side_effect=Exception("osascript failed"))
    def test_fallback_on_error(self, mock_run, capsys):
        notify("Title", "Message")
        time.sleep(0.3)
        captured = capsys.readouterr()
        assert "[Notification]" in captured.out
        assert "Title" in captured.out
