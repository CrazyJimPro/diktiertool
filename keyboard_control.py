"""Globale Taste zum Starten/Stoppen und Tippen des erkannten Texts dort, wo
gerade der Cursor steht (pynput).

Unter Windows wird die gewaehlte Taste systemweit verschluckt (sonst oeffnete
z. B. F10 nebenbei die Menueleiste des aktiven Programms). Unter Linux geht das
mit X11 nicht ohne Weiteres - dort kommt die Taste zusaetzlich beim Programm
an. Unter Wayland sieht pynput gar keine globalen Tasten.

Grenzen, die sich nicht umgehen lassen (stehen auch im README): In Fenster
von Programmen, die als Administrator laufen, darf ein normales Programm
unter Windows weder Tasten abfangen noch tippen (UIPI)."""

import os
import queue
import sys
import threading

from diagnostics import log

# Name in den Einstellungen -> (Windows-Virtual-Key, pynput-Key-Name)
HOTKEYS = {
    "F8": (0x77, "f8"),
    "F9": (0x78, "f9"),
    "F10": (0x79, "f10"),
    "F12": (0x7B, "f12"),
    "Pause": (0x13, "pause"),
    "Rollen": (0x91, "scroll_lock"),
}

_WM_KEYDOWN, _WM_KEYUP, _WM_SYSKEYDOWN, _WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105


class KeyboardUnavailable(Exception):
    """pynput fehlt oder findet keine Tastatur-Schnittstelle (Wayland ...)."""


def _keyboard():
    try:
        from pynput import keyboard
    except Exception as exc:  # ImportError, aber unter Linux auch Xlib-Fehler ohne DISPLAY
        raise KeyboardUnavailable(str(exc))
    return keyboard


class HotkeyListener:
    """Ruft on_press/on_release in einem eigenen Thread auf. Der Windows-Hook
    selbst muss in Millisekunden zurueckkehren - braucht er zu lange, entfernt
    Windows ihn stillschweigend, und die Taste waere bis zum Neustart tot."""

    def __init__(self, key_name: str, on_press, on_release):
        self.key_name = key_name
        self._on_press = on_press
        self._on_release = on_release
        self._events: queue.Queue = queue.Queue()
        self._down = False
        self._listener = None

    def start(self):
        keyboard = _keyboard()
        vk, pynput_name = HOTKEYS[self.key_name]
        if sys.platform == "win32":
            def win32_filter(msg, data):
                # Bewusst auch per Software gesendete Tasten (AutoHotkey,
                # Maustasten-Software, Fernsteuerung) - eigenes Tippen erzeugt
                # ohnehin nie eine dieser Tasten.
                if data.vkCode != vk:
                    return True
                if msg in (_WM_KEYDOWN, _WM_SYSKEYDOWN):
                    self._key_event(True)
                elif msg in (_WM_KEYUP, _WM_SYSKEYUP):
                    self._key_event(False)
                self._listener.suppress_event()  # Taste erreicht kein anderes Programm

            self._listener = keyboard.Listener(win32_event_filter=win32_filter)
        else:
            target = getattr(keyboard.Key, pynput_name)

            # Kein "return key == target and ...": gibt ein pynput-Callback
            # False zurueck, beendet das den ganzen Listener.
            def on_press(key):
                if key == target:
                    self._key_event(True)

            def on_release(key):
                if key == target:
                    self._key_event(False)

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        try:
            self._listener.start()
            self._listener.wait()
        except Exception as exc:
            raise KeyboardUnavailable(str(exc))
        threading.Thread(target=self._dispatch, daemon=True, name="hotkey").start()
        log.info("Taste %s aktiv", self.key_name)

    def _key_event(self, pressed: bool):
        # Gedrueckt halten schickt laufend weitere "gedrueckt" - nur der erste zaehlt
        if pressed == self._down:
            return
        self._down = pressed
        self._events.put(pressed)

    def _dispatch(self):
        while True:
            pressed = self._events.get()
            if pressed is None:
                return
            try:
                (self._on_press if pressed else self._on_release)()
            except Exception:
                log.exception("Fehler bei der Taste %s", self.key_name)

    def stop(self):
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._events.put(None)


class TextTyper:
    """Tippt erkannte Haeppchen ins gerade aktive Fenster - nacheinander in
    einem eigenen Thread, damit langsames Tippen nie die Erkennung aufhaelt.
    Zwischen zwei Haeppchen kommt ein Leerzeichen, ein Zeilenumbruch wird zu
    Enter."""

    def __init__(self, own_window_focused):
        self._own_window_focused = own_window_focused
        self._queue: queue.Queue = queue.Queue()
        self._at_line_start = True
        self._controller = None
        threading.Thread(target=self._worker, daemon=True, name="typer").start()

    def new_session(self):
        """Beim Start einer Aufnahme: das erste Haeppchen ohne Leerzeichen davor."""
        self._queue.put(("reset", None))

    def type_chunk(self, text: str):
        self._queue.put(("text", text))

    def _worker(self):
        while True:
            kind, text = self._queue.get()
            if kind == "reset":
                self._at_line_start = True
                continue
            if self._own_window_focused():
                # Steht der Cursor im Diktiertool selbst, landet der Text ohnehin im
                # Fenster - zusaetzliches Tippen wuerde dort nur Tastenkuerzel ausloesen.
                continue
            # "" heisst: das Haeppchen bestand nur aus "neuer Absatz"
            out = text if text else "\n\n"
            if not self._at_line_start and not out.startswith("\n"):
                out = " " + out
            try:
                if self._controller is None:
                    self._controller = _keyboard().Controller()
                self._controller.type(out)
                self._at_line_start = out.endswith("\n")
            except Exception as exc:
                log.warning("Tippen fehlgeschlagen: %s", exc)


def own_window_has_focus_win32() -> bool:
    """Gehoert das Vordergrundfenster zu diesem Prozess? Zuverlaessiger als
    focus/blur im Browser-Teil, das z. B. beim Klick in die Titelleiste nicht
    immer feuert."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


def beep(start: bool):
    """Kurzer Signalton - hoch beim Start, tiefer beim Stopp. Blockiert ~0,1 s."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(880 if start else 587, 110)
        else:
            import numpy as np
            import sounddevice as sd
            rate = 44100
            t = np.arange(int(rate * 0.11)) / rate
            tone = 0.25 * np.sin(2 * np.pi * (880 if start else 587) * t)
            sd.play(tone.astype("float32"), rate, blocking=True)
    except Exception as exc:  # kein Ausgabegeraet o. ae. - dann eben ohne Ton
        log.info("Signalton nicht moeglich: %s", exc)
