"""Zweite Erkennungs-Engine: Parakeet (deutsch) ueber sherpa-onnx.

Modell: flozen1981/parakeet-primeline-onnx - ein int8-ONNX-Export von
primeline/parakeet-primeline, einem deutschen Fine-Tune von NVIDIAs
parakeet-tdt-0.6b-v3. Lizenz CC-BY-4.0 (Namensnennung: primeline fuer den
Fine-Tune, NVIDIA fuer Basismodell und Architektur) - steht auch im README und
in den Einstellungen.

Nach dem Vorbild von winidi/dictate (local_stt.py), mit zwei Abweichungen:
- Audio wird an Sprechpausen in Stuecke von hoechstens MAX_PIECE_S geteilt,
  nicht in 90-s-Bloecke. Der Speicherbedarf des Encoders waechst quadratisch
  mit der Laenge (gemessen: 90 s -> ~3 GB), und die Pausen liefern zugleich
  die Absatzgrenzen fuer Audiodateien (Transcriber.Paragraphs).
- Pegelanhebung macht schon der Transcriber (diagnostics.normalize_gain).

Bewusst erst beim ersten Gebrauch importiert: sherpa-onnx bringt eine eigene
onnxruntime.dll mit. Wer bei Whisper bleibt, hat sie nie im Prozess.

Gemessen (Machbarkeitstest 10.10.2026, 4 Threads): 5 s Satz in 0,4 s (Whisper
small 2,3 s), 5,5 min Audio in 28 s; Whisper und Parakeet im selben Prozess im
Wechsel ohne Probleme; bei Stille/Rauschen kein erfundener Text."""

from dataclasses import dataclass

import numpy as np

MODEL_REPO = "flozen1981/parakeet-primeline-onnx"
# Feste Revision: jeder bekommt genau die Dateien, mit denen getestet wurde
MODEL_REVISION = "d548e25b9bfe559aa274f361892dc4ed5d64743a"
MODEL_FILES = [
    "encoder.int8.onnx",
    "encoder.int8.onnx.data",   # 620 MB Gewichte - muss neben encoder.int8.onnx liegen
    "decoder.int8.onnx",
    "joiner.int8.onnx",
    "tokens.txt",
]
SAMPLE_RATE = 16000

MAX_PIECE_S = 25.0       # laengstes Stueck am Stueck (Speicher, siehe oben)
RETRY_PIECE_S = 12.0     # leeres Ergebnis bei langem Stueck -> kleiner nochmal
PAUSE_SPLIT_S = 0.5      # ab dieser Pause darf geschnitten werden
NEW_PIECE_PAUSE_S = 2.0  # ab dieser Pause immer ein neues Stueck (= Absatzgrenze)
_FRAME_S = 0.05
_SPEECH_RMS = 0.015      # nach Pegelanhebung (Spitze 0.5) - wie SILENCE_THRESHOLD_RMS


@dataclass
class Segment:
    """Gleiche Grundform wie ein faster-whisper-Segment (start, end, text)."""
    start: float
    end: float
    text: str


def ensure_model() -> str:
    """Pfad zum Modellordner; laedt beim ersten Mal herunter (~640 MB) - in
    denselben Zwischenspeicher wie die Whisper-Modelle (unter Windows der
    model-cache-Ordner der Installation, siehe transcriber.py)."""
    from huggingface_hub import snapshot_download
    return snapshot_download(MODEL_REPO, revision=MODEL_REVISION, allow_patterns=MODEL_FILES)


class ParakeetEngine:
    def __init__(self, num_threads: int):
        import sherpa_onnx  # erst hier, siehe Modul-Doku
        import os
        model_dir = ensure_model()
        path = lambda name: os.path.join(model_dir, name)
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=path("encoder.int8.onnx"),
            decoder=path("decoder.int8.onnx"),
            joiner=path("joiner.int8.onnx"),
            tokens=path("tokens.txt"),
            model_type="nemo_transducer",
            num_threads=num_threads,
            decoding_method="greedy_search",
        )
        # Ohne Aufwaermen dauert die erste echte Erkennung etwa doppelt so lang
        for _ in range(2):
            self._decode(np.zeros(SAMPLE_RATE, dtype=np.float32))

    def _decode(self, audio: np.ndarray) -> str:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, audio)
        self._recognizer.decode_stream(stream)
        return stream.result.text.strip()

    def transcribe(self, audio: np.ndarray):
        """Generator von Segmenten - wie bei faster-whisper wird erst beim
        Durchlaufen gerechnet (Fortschritt und Abbrechen bei Dateien)."""
        for start, end in split_on_pauses(audio):
            piece = audio[int(start * SAMPLE_RATE):int(end * SAMPLE_RATE)]
            text = self._decode(piece)
            # Das Modell liefert ab und zu fuer ein laengeres Stueck mit
            # eindeutiger Sprache gar nichts - kuerzere Teile davon klappen.
            if not text and end - start > RETRY_PIECE_S:
                parts = (self._decode(p) for p in _fixed_split(piece, RETRY_PIECE_S))
                text = " ".join(t for t in parts if t)
            if text:
                yield Segment(start, end, text)


def split_on_pauses(audio: np.ndarray) -> list[tuple[float, float]]:
    """Sprachbereiche (start, end) in Sekunden: an Pausen geschnitten, kurze
    Bereiche zusammengefasst, solange das Stueck MAX_PIECE_S nicht
    ueberschreitet und keine lange Pause dazwischen liegt. Reine Stille ->
    leere Liste."""
    frame = int(_FRAME_S * SAMPLE_RATE)
    n = len(audio) // frame
    if n == 0:
        return []
    rms = np.sqrt(np.mean(audio[:n * frame].reshape(n, frame) ** 2, axis=1))
    speech = rms > _SPEECH_RMS

    # zusammenhaengende Sprachbereiche, Luecken unter PAUSE_SPLIT_S ueberbruecken
    regions = []
    i = 0
    while i < n:
        if not speech[i]:
            i += 1
            continue
        j = i
        while j < n and speech[j]:
            j += 1
        if regions and (i - regions[-1][1]) * _FRAME_S < PAUSE_SPLIT_S:
            regions[-1][1] = j
        else:
            regions.append([i, j])
        i = j

    # benachbarte Bereiche zu Stuecken buendeln (mehr Zusammenhang = bessere Erkennung)
    pieces = []
    for start, end in regions:
        if pieces:
            gap = (start - pieces[-1][1]) * _FRAME_S
            if gap < NEW_PIECE_PAUSE_S and (end - pieces[-1][0]) * _FRAME_S <= MAX_PIECE_S:
                pieces[-1][1] = end
                continue
        pieces.append([start, end])

    # etwas Luft um jedes Stueck (Anlaute/Ausklang), zu lange Stuecke zerteilen
    pad = int(0.2 / _FRAME_S)
    out = []
    for start, end in pieces:
        s, e = max(0, start - pad) * _FRAME_S, min(n, end + pad) * _FRAME_S
        while e - s > MAX_PIECE_S:
            cut = _quietest_cut(rms, s, s + MAX_PIECE_S)
            out.append((s, cut))
            s = cut
        out.append((s, e))
    return out


def _quietest_cut(rms: np.ndarray, start_s: float, end_s: float) -> float:
    """Leisester Moment in den letzten 5 s vor end_s - dort zerteilen."""
    lo = int(max(start_s, end_s - 5.0) / _FRAME_S)
    hi = int(end_s / _FRAME_S)
    return (lo + int(np.argmin(rms[lo:hi]))) * _FRAME_S


def _fixed_split(audio: np.ndarray, piece_s: float):
    step = int(piece_s * SAMPLE_RATE)
    for k in range(0, len(audio), step):
        yield audio[k:k + step]
