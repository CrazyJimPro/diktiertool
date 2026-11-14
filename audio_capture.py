import queue
import sys
import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd

from config import (
    SAMPLE_RATE,
    CHANNELS,
    BLOCKSIZE,
    SILENCE_THRESHOLD_RMS,
    MIN_SPEECH_THRESHOLD_RMS,
    NOISE_FLOOR_FACTOR,
    NOISE_WINDOW_S,
    SILENCE_DURATION_MS,
    MAX_CHUNK_DURATION_S,
    MIN_CHUNK_DURATION_MS,
    MUTE_THRESHOLD_RMS,
    LEVEL_HINT_AFTER_S,
    PRE_ROLL_MS,
)


def _wasapi_hostapi_index():
    """Index der WASAPI-Host-API, oder None (auch auf allem ausser Windows)."""
    if sys.platform != "win32":
        return None
    for idx, hostapi in enumerate(sd.query_hostapis()):
        if "WASAPI" in hostapi["name"]:
            return idx
    return None


def _is_wasapi_device(device) -> bool:
    if _wasapi_hostapi_index() is None:
        return False
    try:
        info = sd.query_devices(device if device is not None else sd.default.device[0])
        return "WASAPI" in sd.query_hostapis(info["hostapi"])["name"]
    except (sd.PortAudioError, ValueError, TypeError):
        return False


def wasapi_extra_settings(device):
    """WASAPI laeuft im Shared Mode mit dem Mischformat des Geraets (meist
    48kHz) und lehnt einen 16kHz-Stream sonst rundheraus ab ("Invalid sample
    rate"). auto_convert schaltet die Abtastratenwandlung von PortAudio an.
    Nur fuer WASAPI-Geraete - an einem MME-Geraet wuerde die Einstellung
    ihrerseits einen Fehler ausloesen."""
    if _is_wasapi_device(device):
        return sd.WasapiSettings(auto_convert=True)
    return None


def list_input_devices():
    """Liefert (index, name) für alle Geräte mit Mikrofon-Eingang.

    Unter Windows nur die der WASAPI-Host-API: PortAudio meldet dort jedes
    Mikrofon einmal pro Host-API (MME, DirectSound, WASAPI, WDM-KS), ein
    einziges Headset erscheint in der Liste also bis zu sechsmal. MME kuerzt
    Geraetenamen zudem hart auf 31 Zeichen ("Mikrofon (High Definition Audio"
    ohne schliessende Klammer). WASAPI ist die moderne Schnittstelle, liefert
    vollstaendige Namen und kennt jedes Geraet genau einmal."""
    devices = sd.query_devices()
    wasapi = _wasapi_hostapi_index()

    if wasapi is not None:
        wasapi_inputs = [
            (idx, d["name"])
            for idx, d in enumerate(devices)
            if d["max_input_channels"] > 0 and d["hostapi"] == wasapi
        ]
        # Nur wenn WASAPI ueberhaupt Geraete meldet - sonst lieber die
        # vollstaendige (unschoene) Liste als gar keine Auswahl.
        if wasapi_inputs:
            return wasapi_inputs

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
        self._preroll_s = 0.0
        self._silence_ms = 0.0
        self._in_speech = False
        # Die letzten Bloecke VOR dem ersten lauten - Anlaute wie "s", "f",
        # "h" liegen oft unter der Sprachschwelle und fehlten sonst am Anfang
        # jedes Haeppchens.
        self._pre_roll = deque(maxlen=max(1, round(PRE_ROLL_MS / 1000 * SAMPLE_RATE / BLOCKSIZE)))
        # Bis hierhin (time.monotonic) Bloecke verwerfen - fuer den Signalton,
        # der sonst selbst mit aufgenommen wuerde
        self._ignore_until = 0.0
        self._on_first_block = None

        # Anpassungsfaehige Sprachschwelle (siehe config.py)
        self._recent_rms = deque(maxlen=max(10, round(NOISE_WINDOW_S * SAMPLE_RATE / BLOCKSIZE)))
        self._threshold = SILENCE_THRESHOLD_RMS
        self._near_run = 0
        self._chunk_peak_rms = 0.0
        self._reset_stats()

        self._level_lock = threading.Lock()
        self._level = 0.0
        # Fuer den Stumm-/Zu-leise-Hinweis: wann zuletzt ueberhaupt Ton bzw.
        # Ton ueber der Sprachschwelle kam (nur zwei Zeitstempel - der
        # Callback soll schlank bleiben).
        self._last_sound_time = time.monotonic()
        self._last_speech_time = time.monotonic()

    def level_problem(self) -> str | None:
        """"stumm", wenn seit LEVEL_HINT_AFTER_S praktisch digitale Stille kam
        (Mikrofon stummgeschaltet, falsches Geraet, Datenschutz-Sperre), "leise",
        wenn nichts die Sprachschwelle erreichte - dann entsteht gar kein
        Haeppchen, und es wuerde nie Text erscheinen. Sonst None."""
        now = time.monotonic()
        if now - self._last_sound_time >= LEVEL_HINT_AFTER_S:
            return "stumm"
        if now - self._last_speech_time >= LEVEL_HINT_AFTER_S:
            return "leise"
        return None

    def _reset_stats(self):
        self._stats_min = None
        self._stats_max = None
        self._stats_near = 0       # Ansaetze knapp unter der Schwelle (evtl. verlorene Woerter)
        self._stats_quiet = 0      # Haeppchen, die die alte feste Schwelle nie erreicht haetten
        self._stats_chunks = 0

    def _update_threshold(self, rms: float):
        """Schwelle = Grundrauschen x Faktor. Grundrauschen ist das leiseste
        Zehntel der letzten Sekunden - auch beim Sprechen gibt es zwischen den
        Woertern genug leise Bloecke. Nur Rechnen auf ~60 Zahlen, im Callback
        unbedenklich."""
        self._recent_rms.append(rms)
        if len(self._recent_rms) < 10:
            return  # gerade erst gestartet - bis dahin die alte feste Schwelle
        ordered = sorted(self._recent_rms)
        floor = ordered[len(ordered) // 10]
        self._threshold = min(SILENCE_THRESHOLD_RMS,
                              max(MIN_SPEECH_THRESHOLD_RMS, floor * NOISE_FLOOR_FACTOR))
        if self._stats_min is None or self._threshold < self._stats_min:
            self._stats_min = self._threshold
        if self._stats_max is None or self._threshold > self._stats_max:
            self._stats_max = self._threshold

    def stats_text(self) -> str:
        """Zusammenfassung fuer das Log beim Aufnahme-Ende (nur Zahlen)."""
        if self._stats_min is None:
            return "schwelle=-"
        return (f"schwelle={self._stats_min:.4f}-{self._stats_max:.4f} haeppchen={self._stats_chunks} "
                f"davon_leise={self._stats_quiet} knapp_darunter={self._stats_near}")

    def ignore_for(self, seconds: float):
        """Die naechsten `seconds` nichts aufnehmen (Signalton ueber die Lautsprecher)."""
        self._ignore_until = time.monotonic() + seconds
        self._pre_roll.clear()

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
        # Der Vorlauf zaehlt fuer die Mindestlaenge nicht mit - sonst kaeme
        # jedes Klicken (50 ms laut + 400 ms Vorlauf) als Haeppchen durch.
        duration_ms = (self._chunk_duration_s - self._preroll_s) * 1000
        chunk = np.concatenate(self._chunk_blocks)
        chunk_peak_rms, self._chunk_peak_rms = self._chunk_peak_rms, 0.0
        self._chunk_blocks = []
        self._chunk_duration_s = 0.0
        self._preroll_s = 0.0
        self._silence_ms = 0.0
        self._in_speech = False

        if duration_ms >= MIN_CHUNK_DURATION_MS:
            self._stats_chunks += 1
            if chunk_peak_rms <= SILENCE_THRESHOLD_RMS:
                self._stats_quiet += 1
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
        if self._on_first_block is not None:
            # Erst jetzt fliesst wirklich Ton - stream.start() kehrt schon
            # 0,1-0,2 s vorher zurueck. Der Aufrufer darf hier nichts
            # Langsames tun (Echtzeit-Thread).
            callback, self._on_first_block = self._on_first_block, None
            callback()
        if self.last_callback_time < self._ignore_until:
            return

        mono = indata[:, 0] if indata.ndim > 1 else indata
        rms = float(np.sqrt(np.mean(np.square(mono))))
        with self._level_lock:
            self._level = rms
        self._update_threshold(rms)
        threshold = self._threshold
        if rms >= MUTE_THRESHOLD_RMS:
            self._last_sound_time = self.last_callback_time
        if rms > threshold:
            self._last_speech_time = self.last_callback_time

        block_duration_s = frames / SAMPLE_RATE

        if rms > threshold:
            self._chunk_peak_rms = max(self._chunk_peak_rms, rms)
            self._near_run = 0
            if not self._in_speech and self._pre_roll:
                self._chunk_blocks.extend(self._pre_roll)
                self._preroll_s = len(self._pre_roll) * block_duration_s
                self._chunk_duration_s += self._preroll_s
                self._pre_roll.clear()
            self._in_speech = True
            self._silence_ms = 0.0
            self._chunk_blocks.append(mono.copy())
            self._chunk_duration_s += block_duration_s
        elif not self._in_speech:
            self._pre_roll.append(mono.copy())
            # Mitzaehlen fuers Log: mindestens 150 ms knapp unter der Schwelle
            # (halbe Schwelle bis Schwelle) - da koennte ein leises Wort gewesen sein
            if rms >= threshold / 2:
                self._near_run += 1
                if self._near_run == 3:
                    self._stats_near += 1
            else:
                self._near_run = 0
        else:
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

    def start(self, on_first_block=None):
        """on_first_block: wird einmal aufgerufen, sobald der erste Audioblock
        ankommt (im Audio-Thread - nur Schnelles, z. B. einen Thread starten)."""
        self._stopping = False
        self._on_first_block = on_first_block
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCKSIZE,
                device=self.device,
                callback=self._callback,
                finished_callback=self._on_finished,
                extra_settings=wasapi_extra_settings(self.device),
            )
            self.last_callback_time = time.monotonic()
            self._last_sound_time = self.last_callback_time
            self._last_speech_time = self.last_callback_time
            self._pre_roll.clear()
            self._ignore_until = 0.0
            self._recent_rms.clear()
            self._threshold = SILENCE_THRESHOLD_RMS
            self._near_run = 0
            self._chunk_peak_rms = 0.0
            self._reset_stats()
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
