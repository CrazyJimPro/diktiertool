import os
import queue
import threading
import time

import customtkinter as ctk
import sounddevice as sd

from audio_capture import AudioCapture, list_input_devices
from transcriber import Transcriber
from file_writer import FileWriter

POLL_MS = 100
WATCHDOG_TIMEOUT_S = 3.0
STANDARD_LABEL = "Standard-Mikrofon"
# Rein optische Skalierung: RMS-Werte normaler Sprache liegen grob im Bereich
# 0.02-0.15, das soll auf der Pegelanzeige sichtbar ausschlagen statt nur ein
# paar Pixel breit zu sein.
LEVEL_METER_SCALE = 5.0


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Diktiertool")
        self.geometry("640x520")

        self.audio_q: queue.Queue = queue.Queue(maxsize=100)
        self.result_q: queue.Queue = queue.Queue(maxsize=100)
        self.error_q: queue.Queue = queue.Queue(maxsize=20)
        self.stop_event = threading.Event()

        self.writer = FileWriter()
        self.capture = AudioCapture(self.audio_q, self.error_q, device=None)
        self.transcriber = Transcriber(self.audio_q, self.result_q, self.stop_event)

        self.recording = False
        self.device_map = {}

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.start_button.configure(state="disabled")
        self._set_status("Lade Spracherkennungsmodell (beim ersten Mal ca. 500MB, "
                          "kann einige Minuten dauern)...")
        self.transcriber.start()

        self.after(POLL_MS, self._poll)

    def _build_widgets(self):
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        self.device_var = ctk.StringVar(value=STANDARD_LABEL)
        self.device_dropdown = ctk.CTkOptionMenu(top_frame, variable=self.device_var, values=[STANDARD_LABEL])
        self.device_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.refresh_button = ctk.CTkButton(top_frame, text="Aktualisieren", width=110,
                                             command=self._refresh_devices)
        self.refresh_button.pack(side="left")

        self.start_button = ctk.CTkButton(self, text="Start", command=self._toggle_recording)
        self.start_button.pack(pady=(0, 5))

        self.status_label = ctk.CTkLabel(self, text="Initialisiere...")
        self.status_label.pack(pady=(0, 5))

        self.level_bar = ctk.CTkProgressBar(self, width=300)
        self.level_bar.set(0)
        self.level_bar.pack(pady=(0, 10))

        self.text_box = ctk.CTkTextbox(self, wrap="word")
        self.text_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.text_box.configure(state="disabled")

        self._refresh_devices()

    def _refresh_devices(self):
        self.device_map = {STANDARD_LABEL: None}
        for idx, name in list_input_devices():
            self.device_map[f"[{idx}] {name}"] = idx
        labels = list(self.device_map.keys())
        self.device_dropdown.configure(values=labels)
        if self.device_var.get() not in labels:
            self.device_var.set(labels[0])

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    def _append_text(self, text: str):
        self.text_box.configure(state="normal")
        self.text_box.insert("end", text + "\n")
        self.text_box.see("end")
        self.text_box.configure(state="disabled")

    def _toggle_recording(self):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self.capture.device = self.device_map.get(self.device_var.get())
        try:
            self.capture.start()
        except sd.PortAudioError as exc:
            self._set_status(f"Fehler: Gerät nicht verfügbar ({exc})")
            return

        self.writer.start_session()
        self.recording = True
        self.start_button.configure(text="Stop")
        self.device_dropdown.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self._set_status("Nimmt auf...")

    def _stop_recording(self):
        self.capture.stop()
        self.recording = False
        self.start_button.configure(text="Start")
        self.device_dropdown.configure(state="normal")
        self.refresh_button.configure(state="normal")
        self._set_status("Bereit")

    def _handle_error(self, message: str):
        if self.recording:
            self.capture.stop()
            self.recording = False
            self.start_button.configure(text="Start")
            self.device_dropdown.configure(state="normal")
            self.refresh_button.configure(state="normal")
        self._set_status(f"Fehler: {message} – Gerät neu auswählen und Start drücken")

    def _poll(self):
        try:
            while True:
                msg = self.result_q.get_nowait()
                if msg["type"] == "model_ready":
                    self.start_button.configure(state="normal")
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

        if self.recording:
            self.level_bar.set(min(self.capture.get_level() * LEVEL_METER_SCALE, 1.0))
        else:
            self.level_bar.set(0)

        self.after(POLL_MS, self._poll)

    def _on_close(self):
        self.stop_event.set()
        if self.recording:
            self.capture.stop()
        self.destroy()
        # Siehe main.py: regulaeres Python-Shutdown stuerzt beim Aufraeumen von
        # ctranslate2/oneDNN reproduzierbar ab, daher direkter Prozess-Exit.
        os._exit(0)


def main():
    ctk.set_appearance_mode("system")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
