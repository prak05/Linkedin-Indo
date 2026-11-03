import pytest

import desktop
import local_server


@pytest.fixture
def quiet(monkeypatch):
    monkeypatch.setattr(local_server.Handler, "log_message", lambda *a: None)
    monkeypatch.setattr(desktop, "tell", lambda *a, **k: None)


def test_app_window_uses_its_own_profile_and_window_class(tmp_path):
    cmd = desktop.app_window_cmd("/usr/bin/chromium", "http://localhost:8787/", tmp_path)
    assert cmd[0] == "/usr/bin/chromium" and "--app=http://localhost:8787/" in cmd
    assert f"--user-data-dir={tmp_path}" in cmd and "--class=LinkedInIndo" in cmd


def test_browser_choice_prefers_env_then_chromium_family(monkeypatch):
    found = {"brave-browser": "/usr/bin/brave-browser", "my-browser": "/opt/my-browser"}
    monkeypatch.setattr(desktop.shutil, "which", lambda name: found.get(name))
    monkeypatch.delenv("INDO_BROWSER", raising=False)
    assert desktop.find_browser() == "/usr/bin/brave-browser"
    monkeypatch.setenv("INDO_BROWSER", "my-browser")
    assert desktop.find_browser() == "/opt/my-browser"
    found.clear()
    monkeypatch.delenv("INDO_BROWSER")
    assert desktop.find_browser() is None


def test_backend_starts_once_and_a_second_launch_reuses_it(quiet):
    server = local_server.make_server(port=0)
    port = server.server_address[1]
    server.server_close()

    first = desktop.start_server(port)
    try:
        assert first is not None and desktop.running_here(port)
        assert desktop.start_server(port) is None  # second window: reuse, never stop the first one's backend
    finally:
        first.shutdown()
        first.server_close()
    assert not desktop.running_here(port)


def test_a_foreign_program_on_the_port_is_reported(quiet, monkeypatch):
    def busy(port):
        raise OSError("in use")

    monkeypatch.setattr(desktop, "running_here", lambda port: False)
    monkeypatch.setattr(local_server, "make_server", busy)
    with pytest.raises(SystemExit):
        desktop.start_server(8787)


def test_closing_the_window_stops_the_backend(quiet, monkeypatch, tmp_path):
    server = local_server.make_server(port=0)
    port = server.server_address[1]
    server.server_close()
    monkeypatch.setattr(desktop, "PORT", port)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop, "find_browser", lambda: "/usr/bin/chromium")
    seen = {}

    def window(cmd, **kwargs):
        # While the window is "open" the backend answers; returning means the user closed it.
        seen["live"] = desktop.running_here(port)
        seen["cmd"] = cmd

    monkeypatch.setattr(desktop.subprocess, "run", window)
    assert desktop.main() == 0
    assert seen["live"] and f"--app=http://localhost:{port}/" in seen["cmd"]
    assert (tmp_path / "linkedin-indo" / "window").is_dir()
    assert not desktop.running_here(port)
