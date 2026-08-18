import queue
import threading
import time

import numpy as np
import sounddevice as sd

from config import (
    SAMPLE_RATE,
    CHANNELS,
    BLOCKSIZE,
    SILENCE_THRESHOLD_RMS,
    SILENCE_DURATION_MS,
    MAX_CHUNK_DURATION_S,
    MIN_CHUNK_DURATION_MS,
)


def list_input_devices():
    """Liefert (index, name) für alle Geräte mit Mikrofon-Eingang."""
    devices = sd.query_devices()
    return [
        (idx, d["name"])
        for idx, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


class AudioCapture:
    """Nimmt Mikrofonaudio auf und liefert fertige Sprach-Häppchen (nach Pausenerkennung)
    über audio_q. Der sounddevice-Callback läuft in einem eigenen, echtzeitkritischen
    Thread und macht dort bewusst nur minimale Arbeit (kein Whisper, kein Datei-I/O,
    keine GUI-Zugriffe) - sonst drohen Aussetzer in der Aufnahme."""

    def __init__(self, audio_q: queue.Queue, error_q: queue.Queue, device=None):
        self.audio_q = audio_q
        self.error_q = error_q
        self.device = device
        self.stream = None
        self.last_callback_time = time.monotonic()
        self._stopping = False

        self._chunk_blocks = []
        self._chunk_duration_s = 0.0
        self._silence_ms = 0.0
        self._in_speech = False

        self._level_lock = threading.Lock()
        self._level = 0.0

    def get_level(self) -> float:
        with self._level_lock:
            return self._level

    def _push_error(self, message: str):
        try:
            self.error_q.put_nowait(message)
        except queue.Full:
            pass

    def _finalize_chunk(self):
        if not self._chunk_blocks:
            return
        duration_ms = self._chunk_duration_s * 1000
        chunk = np.concatenate(self._chunk_blocks)
        self._chunk_blocks = []
        self._chunk_duration_s = 0.0
        self._silence_ms = 0.0
        self._in_speech = False

        if duration_ms >= MIN_CHUNK_DURATION_MS:
            try:
                self.audio_q.put_nowait(chunk)
            except queue.Full:
                self._push_error("Erkennung kommt nicht hinterher, Häppchen verworfen")

    def _callback(self, indata, frames, time_info, status):
        # Absichtlich KEIN _push_error() bei "status" (z.B. input_overflow):
        # das sind meist kurze, harmlose Aussetzer unter Systemlast und kein
        # Zeichen fuer ein getrenntes Geraet. Ein echtes Verbindungsende wird
        # zuverlaessiger ueber den Watchdog (keine Callbacks mehr) oder
        # finished_callback erkannt.
        self.last_callback_time = time.monotonic()

        mono = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(np.square(mono))))
        with self._level_lock:
            self._level = rms

        block_duration_s = frames / SAMPLE_RATE

        if rms > SILENCE_THRESHOLD_RMS:
            self._in_speech = True
            self._silence_ms = 0.0
            self._chunk_blocks.append(mono.copy())
            self._chunk_duration_s += block_duration_s
        elif self._in_speech:
            self._chunk_blocks.append(mono.copy())
            self._chunk_duration_s += block_duration_s
            self._silence_ms += block_duration_s * 1000
            if self._silence_ms >= SILENCE_DURATION_MS:
                self._finalize_chunk()
                return

        if self._chunk_duration_s >= MAX_CHUNK_DURATION_S:
            self._finalize_chunk()

    def _on_finished(self):
        if not self._stopping:
            self._push_error("Audio-Stream unerwartet beendet (Gerät getrennt?)")

    def start(self):
        self._stopping = False
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCKSIZE,
                device=self.device,
                callback=self._callback,
                finished_callback=self._on_finished,
            )
            self.last_callback_time = time.monotonic()
            self.stream.start()
        except sd.PortAudioError as exc:
            self.stream = None
            self._push_error(f"Gerät nicht verfügbar: {exc}")
            raise

    def stop(self):
        self._stopping = True
        if self.stream is not None:
            self._finalize_chunk()
            try:
                self.stream.stop()
                self.stream.close()
            except sd.PortAudioError:
                pass
            self.stream = None
