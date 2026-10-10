"""Sorgt dafuer, dass das Diktiertool nur einmal laeuft.

Zwei Fenster gleichzeitig gehen schief: pywebview nimmt bei
private_mode=False immer denselben Port (42001, damit localStorage mit der
Design-Wahl erhalten bleibt). Das zweite Fenster zeigt dann die Seite des
ersten, und beide schreiben in dieselbe Datei.

Ablauf: Die erste Instanz sperrt eine Lock-Datei und lauscht auf einem
zufaelligen Port nur auf 127.0.0.1, den sie in eine zweite Datei schreibt. Eine
weitere Instanz bekommt die Sperre nicht, meldet sich ueber diesen Port und
beendet sich - die erste holt daraufhin ihr Fenster nach vorne.

Die Sperre haengt am offenen Dateihandle: Stuerzt das Programm ab oder endet
per os._exit(), gibt das Betriebssystem sie sofort frei. Eine liegen
gebliebene Lock-Datei blockiert also nie den naechsten Start."""

import os
import socket
import sys
import threading
import time
from pathlib import Path

LOCK_NAME = "instance.lock"
PORT_NAME = "instance.port"
WAKE_MESSAGE = b"show"


def _try_lock(handle) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


class InstanceGuard:
    def __init__(self, lock_dir: Path, lock_handle):
        self._lock_dir = lock_dir
        self._lock_handle = lock_handle  # muss offen bleiben, solange das Programm laeuft
        self._server = None

    def listen(self, on_wake):
        """Startet den Empfang von Weckrufen weiterer Instanzen. on_wake laeuft
        in einem eigenen Thread."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        self._server = server
        try:
            (self._lock_dir / PORT_NAME).write_text(str(server.getsockname()[1]), encoding="ascii")
        except OSError:
            return  # Ohne Portdatei kann niemand wecken - laufen darf das Tool trotzdem

        def serve():
            while True:
                try:
                    conn, _ = server.accept()
                except OSError:
                    return
                with conn:
                    conn.settimeout(1.0)
                    try:
                        if conn.recv(16) == WAKE_MESSAGE:
                            on_wake()
                    except OSError:
                        pass

        threading.Thread(target=serve, daemon=True).start()


def acquire(lock_dir: Path) -> InstanceGuard | None:
    """InstanceGuard, wenn dies die erste Instanz ist, sonst None. Laesst sich
    die Lock-Datei gar nicht anlegen (Ordner schreibgeschuetzt o. ae.), gilt das
    nicht als "laeuft schon" - lieber zwei Fenster als gar keins."""
    try:
        lock_dir.mkdir(parents=True, exist_ok=True)
        handle = open(lock_dir / LOCK_NAME, "a+b")
    except OSError:
        return InstanceGuard(lock_dir, None)
    if not _try_lock(handle):
        handle.close()
        return None
    return InstanceGuard(lock_dir, handle)


def wake_running_instance(lock_dir: Path, timeout_s: float = 3.0) -> bool:
    """Bittet die laufende Instanz, ihr Fenster zu zeigen. Startet sie gerade
    erst selbst (Doppelklick doppelt ausgeloest), steht die Portdatei evtl.
    noch nicht - deshalb ein paar Versuche."""
    if sys.platform == "win32":
        # Windows laesst nur den Prozess mit der letzten Benutzereingabe ein
        # Fenster in den Vordergrund holen - das ist dieser hier (gerade per
        # Doppelklick gestartet). Er reicht das Recht an die laufende Instanz
        # weiter, sonst blinkt dort nur der Taskleisten-Knopf.
        try:
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        except (AttributeError, OSError):
            pass

    deadline = time.monotonic() + timeout_s
    while True:
        try:
            port = int((lock_dir / PORT_NAME).read_text(encoding="ascii").strip())
            with socket.create_connection(("127.0.0.1", port), timeout=1.0) as conn:
                conn.sendall(WAKE_MESSAGE)
            return True
        except (OSError, ValueError):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.3)
