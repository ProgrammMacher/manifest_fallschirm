import sys
import socket
import threading
import time
import os
import subprocess
import webbrowser
from contextlib import closing

from app import create_app

app = create_app()

HOST = "0.0.0.0"
PORT = 5000
OPEN_URL = "http://127.0.0.1:5000/pwa/"


def _port_in_use(port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _open_browser_when_ready() -> None:
    for _ in range(30):
        if _port_in_use(PORT):
            try:
                if os.name == "nt":
                    subprocess.Popen(
                        ["cmd", "/c", "start", "", OPEN_URL],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    opened = True
                else:
                    opened = webbrowser.open(OPEN_URL)

                if opened:
                    print(f"[MANIFEST] Browser geöffnet: {OPEN_URL}", flush=True)
                else:
                    print(
                        f"[MANIFEST][WARN] Browser konnte nicht automatisch geöffnet werden: {OPEN_URL}",
                        flush=True,
                    )
            except Exception as exc:
                try:
                    opened = webbrowser.open(OPEN_URL)
                    if opened:
                        print(f"[MANIFEST] Browser geöffnet (Fallback): {OPEN_URL}", flush=True)
                    else:
                        print(
                            f"[MANIFEST][WARN] Browser konnte nicht automatisch geöffnet werden: {OPEN_URL}",
                            flush=True,
                        )
                except Exception:
                    print(f"[MANIFEST][WARN] Browser konnte nicht geöffnet werden: {exc}", flush=True)
            return
        time.sleep(0.5)

    print(
        "[MANIFEST][WARN] Browser wurde nicht automatisch geöffnet, weil der Server nicht rechtzeitig erreichbar war.",
        flush=True,
    )

if __name__ == "__main__":
    print(f"[MANIFEST] Python executable: {sys.executable}", flush=True)

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
