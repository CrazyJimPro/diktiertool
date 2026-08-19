import math
import os
import queue
import threading
import time

import customtkinter as ctk
import sounddevice as sd

import theme
from level_meter import LevelMeter
from audio_capture import AudioCapture, list_input_devices
from transcriber import Transcriber
from file_writer import FileWriter

POLL_MS = 100
WATCHDOG_TIMEOUT_S = 3.0
STANDARD_LABEL = "Standard-Mikrofon"
# Lineares RMS*SCALE (vorher) reagiert sehr empfindlich auf die Eingangs-
# empfindlichkeit des jeweiligen Mikrofons - bei zwei Versuchen (5.0, dann
# 2.0) blieb die Anzeige bei diesem Nutzer trotzdem staendig im roten
# Bereich. Pegelanzeigen rechnen ueblicherweise in dB statt linear, weil das
# robuster gegenueber genau dieser Empfindlichkeits-Varianz ist. -40dB liegt
# knapp unter SILENCE_THRESHOLD_RMS (~-36.5dB), -3dB ist nah an digitalem
# Clipping (0dB) - nur wirklich lautes/uebersteuerndes Signal soll voll rot
# ausschlagen.
LEVEL_METER_MIN_DB = -40.0
LEVEL_METER_MAX_DB = -3.0


def _level_to_meter(rms: float) -> float:
    if rms <= 0:
        return 0.0
    db = 20 * math.log10(rms)
    span = LEVEL_METER_MAX_DB - LEVEL_METER_MIN_DB
    return max(0.0, min(1.0, (db - LEVEL_METER_MIN_DB) / span))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=theme.BG)
        self.title("Diktiertool")
        self.geometry("660x560")

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
        card = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=theme.CORNER_RADIUS,
                             border_width=1, border_color=theme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        title_label = ctk.CTkLabel(card, text="Diktiertool", text_color=theme.GOLD,
                                    font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(anchor="w", padx=20, pady=(18, 4))

        top_frame = ctk.CTkFrame(card, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(4, 12))

        self.device_var = ctk.StringVar(value=STANDARD_LABEL)
        self.device_dropdown = ctk.CTkOptionMenu(
            top_frame, variable=self.device_var, values=[STANDARD_LABEL],
            fg_color=theme.SURFACE_LIGHT, button_color=theme.GOLD, button_hover_color=theme.GOLD_HOVER,
            text_color=theme.TEXT_PRIMARY, dropdown_fg_color=theme.SURFACE_LIGHT,
            dropdown_hover_color=theme.GOLD, dropdown_text_color=theme.TEXT_PRIMARY,
            corner_radius=theme.CORNER_RADIUS_SMALL)
        self.device_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.refresh_button = ctk.CTkButton(
            top_frame, text="Aktualisieren", width=110, command=self._refresh_devices,
            fg_color=theme.SURFACE_LIGHT, hover_color=theme.BORDER, text_color=theme.TEXT_PRIMARY,
            corner_radius=theme.CORNER_RADIUS_SMALL)
        self.refresh_button.pack(side="left")

        self.start_button = ctk.CTkButton(
            card, text="Start", command=self._toggle_recording, width=200, height=40,
            fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER, text_color=theme.TEXT_ON_ACCENT,
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=theme.CORNER_RADIUS_SMALL)
        self.start_button.pack(pady=(0, 10))

        self.status_label = ctk.CTkLabel(card, text="Initialisiere...", text_color=theme.TEXT_SECONDARY,
                                          font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 8))

        self.level_bar = LevelMeter(card, width=300, height=8)
        self.level_bar.pack(pady=(0, 14))

        self.text_box = ctk.CTkTextbox(card, wrap="word", fg_color=theme.SURFACE_LIGHT,
                                        text_color=theme.TEXT_PRIMARY, border_width=1,
                                        border_color=theme.BORDER, corner_radius=theme.CORNER_RADIUS_SMALL,
                                        scrollbar_button_color=theme.GOLD,
                                        scrollbar_button_hover_color=theme.GOLD_HOVER,
                                        font=ctk.CTkFont(size=13))
        self.text_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
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
        self.start_button.configure(text="Stop", fg_color=theme.RECORDING, hover_color=theme.RECORDING_HOVER)
        self.device_dropdown.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self._set_status("Nimmt auf...")

    def _stop_recording(self):
        self.capture.stop()
        self.recording = False
        self.start_button.configure(text="Start", fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER)
        self.device_dropdown.configure(state="normal")
        self.refresh_button.configure(state="normal")
        self._set_status("Bereit")

    def _handle_error(self, message: str):
        if self.recording:
            self.capture.stop()
            self.recording = False
            self.start_button.configure(text="Start", fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER)
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
            self.level_bar.set(_level_to_meter(self.capture.get_level()))
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
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
