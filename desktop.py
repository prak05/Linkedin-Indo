"""LinkedIn Indo desktop app: starts the local backend and opens the UI in its own window.

Run:  python3.13 desktop.py        (installed as: linkedin-indo-desktop, and in the apps menu)

The window is a Chromium-family browser in app mode (no tabs or address bar) with
its own profile, so closing it ends the process and the backend stops with it.
Without such a browser the page opens in the default browser and the backend runs
until this process is stopped.
"""

import http.client
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import local_server

APP_ID = "LinkedInIndo"
# Cognito's redirect URI and the server's Host check expect this port.
PORT = local_server.PORT
BROWSERS = ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome", "brave-browser",
            "microsoft-edge-stable", "vivaldi-stable")


def data_dir():
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return base / "linkedin-indo"


def tell(message, error=False):
    """Show a message even when started from the apps menu (no terminal)."""
    print(message, file=sys.stderr if error else sys.stdout, flush=True)
    if shutil.which("zenity"):
        subprocess.run(["zenity", "--error" if error else "--info", "--title=LinkedIn Indo", f"--text={message}"],
                       check=False, stderr=subprocess.DEVNULL)
    elif shutil.which("notify-send"):
        subprocess.run(["notify-send", "LinkedIn Indo", message], check=False)


def running_here(port):
    """True if LinkedIn Indo's own backend already answers on this port."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/health", headers={"Host": f"127.0.0.1:{port}"})
        resp = conn.getresponse()
        body = json.loads(resp.read() or b"{}")
        conn.close()
        return resp.getheader("Server", "").startswith("LinkedInIndo") and body.get("target") == "local"
    except (OSError, ValueError):
        return False


def find_browser():
    choice = os.environ.get("INDO_BROWSER")
    if choice:
        return shutil.which(choice)
    return next((path for name in BROWSERS if (path := shutil.which(name))), None)


def app_window_cmd(browser, url, profile):
    return [browser, f"--app={url}", f"--user-data-dir={profile}", f"--class={APP_ID}",
            "--no-first-run", "--no-default-browser-check", "--window-size=1280,860"]


def start_server(port):
    """Start the backend on a thread. Returns the server, or None if one is already running."""
    if running_here(port):
        return None
    try:
        server = local_server.make_server(port)
    except OSError:
        tell(f"Port {port} is in use by another program. Close it, or set INDO_PORT.", error=True)
        raise SystemExit(1) from None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    server = start_server(PORT)
    url = f"http://localhost:{PORT}/"
    browser = find_browser()
    try:
        if browser:
            profile = data_dir() / "window"
            profile.mkdir(parents=True, exist_ok=True)
            # Blocks until the window is closed: the separate profile is its own browser process.
            subprocess.run(app_window_cmd(browser, url, profile), check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(url)
            if server:
                tell(f"LinkedIn Indo is open in your browser at {url}. Install Chromium for an app window. "
                     "The backend runs until you stop this program.")
                threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.shutdown()
            server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
