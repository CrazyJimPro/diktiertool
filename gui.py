import json
import math
import os
import pathlib
import queue
import threading
import time
import webbrowser

import sounddevice as sd
import webview

import config
from update_check import REPO, get_latest_version, is_newer
from audio_capture import AudioCapture, list_input_devices
from transcriber import Transcriber
from file_writer import FileWriter

POLL_S = 0.1
WATCHDOG_TIMEOUT_S = 3.0
STANDARD_LABEL = "Standard-Mikrofon"
WEB_DIR = pathlib.Path(__file__).resolve().parent / "web"

# Lineares RMS*SCALE reagiert sehr empfindlich auf die Eingangsempfindlichkeit
# des jeweiligen Mikrofons - dB ist robuster gegenueber genau dieser Varianz.
# -40dB liegt knapp unter SILENCE_THRESHOLD_RMS (~-36.5dB), -3dB ist nah an
# digitalem Clipping (0dB) - nur wirklich lautes/uebersteuerndes Signal soll
# voll rot ausschlagen.
LEVEL_METER_MIN_DB = -40.0
LEVEL_METER_MAX_DB = -3.0


def _level_to_meter(rms: float) -> float:
    if rms <= 0:
        return 0.0
    db = 20 * math.log10(rms)
    span = LEVEL_METER_MAX_DB - LEVEL_METER_MIN_DB
    return max(0.0, min(1.0, (db - LEVEL_METER_MIN_DB) / span))


class Api:
    """js_api fuer pywebview - Methoden hier sind aus dem Frontend per
    pywebview.api.<name>(...) aufrufbar."""

    def __init__(self, app: "App"):
        self.app = app

    def toggle_recording(self, device_label=None):
        self.app.toggle_recording(device_label)

    def refresh_devices(self, current_label=None):
        self.app.refresh_devices(current_label)

    def open_url(self, url):
        webbrowser.open(url)


class App:
    def __init__(self):
        self.audio_q: queue.Queue = queue.Queue(maxsize=100)
        self.result_q: queue.Queue = queue.Queue(maxsize=100)
        self.error_q: queue.Queue = queue.Queue(maxsize=20)
        self.stop_event = threading.Event()

        self.writer = FileWriter()
        self.capture = AudioCapture(self.audio_q, self.error_q, device=None)
        self.transcriber = Transcriber(self.audio_q, self.result_q, self.stop_event)

        self.recording = False
        self.device_map = {}
        self.window = None

    def run(self):
        self.window = webview.create_window(
            "Diktiertool", url=str(WEB_DIR / "index.html"), width=680, height=780,
            js_api=Api(self),
        )
        self.window.events.loaded += self._on_page_loaded
        self.window.events.closing += self._on_close
        webview.start()

    def _js(self, code: str):
        try:
            self.window.evaluate_js(code)
        except Exception:
            pass  # Fenster evtl. schon am Schliessen - Update darf nicht crashen

    def _on_page_loaded(self):
        self._js(f"setVersion({json.dumps(config.VERSION)}, "
                  f"{json.dumps(f'https://github.com/{REPO}/releases')})")
        self.refresh_devices()
        self._set_status("Lade Spracherkennungsmodell (beim ersten Mal ca. 500MB, "
                          "kann einige Minuten dauern)...")
        self.transcriber.start()

        threading.Thread(target=self._check_for_update, daemon=True).start()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _check_for_update(self):
        latest = get_latest_version()
        if latest and is_newer(latest, config.VERSION):
            self._js(f"showUpdateBadge({json.dumps(latest)}, "
                      f"{json.dumps(f'https://github.com/{REPO}/releases/tag/v{latest}')})")

    def refresh_devices(self, current_label=None):
        self.device_map = {STANDARD_LABEL: None}
        for idx, name in list_input_devices():
            self.device_map[f"[{idx}] {name}"] = idx
        labels = list(self.device_map.keys())
        selected = current_label if current_label in labels else labels[0]
        self._js(f"setDeviceList({json.dumps(labels)}, {json.dumps(selected)})")

    def _set_status(self, text: str):
        self._js(f"setStatus({json.dumps(text)})")

    def _append_text(self, text: str):
        self._js(f"appendText({json.dumps(text)})")

    def toggle_recording(self, device_label=None):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording(device_label)

    def _start_recording(self, device_label):
        self.capture.device = self.device_map.get(device_label)
        try:
            self.capture.start()
        except sd.PortAudioError as exc:
            self._set_status(f"Fehler: Gerät nicht verfügbar ({exc})")
            return

        self.writer.start_session()
        self.recording = True
        self._js("setRecordingState(true)")
        self._set_status("Nimmt auf...")

    def _stop_recording(self):
        self.capture.stop()
        self.recording = False
        self._js("setRecordingState(false)")
        self._set_status("Bereit")

    def _handle_error(self, message: str):
        if self.recording:
            self.capture.stop()
            self.recording = False
            self._js("setRecordingState(false)")
        self._set_status(f"Fehler: {message} – Gerät neu auswählen und Start drücken")

    def _poll_loop(self):
        while not self.stop_event.is_set():
            time.sleep(POLL_S)

            try:
                while True:
                    msg = self.result_q.get_nowait()
                    if msg["type"] == "model_ready":
                        self._js("setModelReady()")
                        self._set_status("Bereit")
                    elif msg["type"] == "text":
                        self._append_text(msg["text"])
                        self.writer.write(msg["text"])
            except queue.Empty:
                pass

            try:
                while True:
                    err = self.error_q.get_nowait()
                    self._handle_error(err)
            except queue.Empty:
                pass

            if self.recording and time.monotonic() - self.capture.last_callback_time > WATCHDOG_TIMEOUT_S:
                self._handle_error("Kein Signal vom Mikrofon mehr - Verbindung verloren?")

            self._js(f"setLevel({_level_to_meter(self.capture.get_level()) if self.recording else 0})")

    def _on_close(self):
        self.stop_event.set()
        if self.recording:
            self.capture.stop()
        # Siehe transcriber.py: regulaeres Python-Shutdown stuerzt beim Aufraeumen
        # von ctranslate2/oneDNN reproduzierbar ab, daher direkter Prozess-Exit.
        os._exit(0)


def main():
    App().run()


if __name__ == "__main__":
    main()
