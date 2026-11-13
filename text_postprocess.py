"""Nachbearbeitung des erkannten Texts: Whisper-Phantomsaetze aussortieren und
gesprochene Befehle ("neuer Absatz", optional "Komma" ...) umsetzen. Bewusst
ohne Abhaengigkeit von faster-whisper, damit es sich ohne Modell pruefen laesst."""

import re

# Whisper wurde u. a. mit untertitelten Fernsehsendungen trainiert und haengt
# bei Stille oder Rauschen gern deren Abspann an. Nur wenn ein ganzes Segment
# aus so einem Satz besteht, wird es verworfen - mitten im Diktat darf
# "vielen Dank" natuerlich vorkommen.
_PHANTOM_PATTERNS = [
    r"untertitel(ung)?\b.*",
    r".*\bim auftrag des (zdf|ard|wdr|ndr|swr|br)\b.*",
    r".*\bamara\.org\b.*",
    r"copyright\b.*",
    r"\(?c\)? ?(zdf|ard|wdr|ndr|swr|br)\b.*",
    r"vielen dank (fürs|für's|für das|für ihr) zu(schauen|hören|sehen)\b.*",
    r"danke (fürs|für's) zu(schauen|hören|sehen)\b.*",
    r"bis zum nächsten mal\W*",
    r"tschüss\W*",
    r"swr \d{4}\W*",
]
_PHANTOM_RE = re.compile(r"^\W*(?:" + "|".join(_PHANTOM_PATTERNS) + r")$", re.IGNORECASE)

# Whispers eigene Schwelle fuer Wiederholungsschleifen ("und dann und dann und
# dann ..."): stark komprimierbarer Text ist fast nie echte Sprache.
MAX_COMPRESSION_RATIO = 2.4
# faster-whisper verwirft bereits Segmente mit no_speech_prob > 0.6 UND
# avg_logprob < -1.0. Zusaetzlich nur, wenn sich das Modell sehr sicher ist,
# dass gar keine Sprache vorlag - eine strengere Schwelle wuerde bei leisen
# Mikrofonen echte Saetze mit wegwerfen.
MAX_NO_SPEECH_PROB = 0.9


def is_phantom(text: str) -> bool:
    return bool(_PHANTOM_RE.match(text.strip()))


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text).split()).casefold()


def _reject_reason(segment, echo: str | None) -> str | None:
    """Grund, ein Segment zu verwerfen, oder None. Die Gruende landen (nur als
    Zaehler, nie mit Text) im Diagnose-Log."""
    if getattr(segment, "compression_ratio", 0) > MAX_COMPRESSION_RATIO:
        return "wiederholung"
    if getattr(segment, "no_speech_prob", 0) > MAX_NO_SPEECH_PROB:
        return "keine_sprache"
    if is_phantom(segment.text):
        return "phantom"
    # Die eigenen Woerter gehen als Prompt ans Modell - bei Stille gibt Whisper
    # den Prompt gern einfach wieder aus ("Meier, Kubernetes, Grundbuchamt").
    if echo and _normalize(segment.text) == echo:
        return "echo"
    # Nur Satzzeichen ("... ... ...") - kommt bei Rauschen vor, mit
    # eigenen Woertern im Prompt deutlich haeufiger
    if not re.search(r"\w", segment.text):
        return "leer"
    return None


def filter_segments(segments, hotwords: str | None = None, rejected=None) -> str:
    """Fuegt die Segmente von model.transcribe() zu Text zusammen und laesst
    dabei vermutlich erfundene weg. rejected (z. B. ein Counter) zaehlt auf
    Wunsch mit, was aus welchem Grund wegfiel."""
    echo = _normalize(hotwords) if hotwords else None
    kept = []
    for segment in segments:
        reason = _reject_reason(segment, echo)
        if reason is None:
            kept.append(segment.text)
        elif rejected is not None:
            rejected[reason] += 1
    return "".join(kept).strip()


# Satzzeichen, die Whisper selbst um einen gesprochenen Befehl setzt
# ("Hallo. Neuer Absatz. Weiter"), gehen mit dem Befehl weg.
_TRAILING_PUNCT = r"[.,;:!?]*"
_PARAGRAPH_RE = re.compile(r"[ ,]*\bneue[rn]?\s+absatz\b" + _TRAILING_PUNCT + r"\s*", re.IGNORECASE)
_LINE_RE = re.compile(r"[ ,]*\bneue\s+zeile\b" + _TRAILING_PUNCT + r"\s*", re.IGNORECASE)

_PUNCTUATION_COMMANDS = {
    "komma": ",",
    "punkt": ".",
    "fragezeichen": "?",
    "ausrufezeichen": "!",
    "doppelpunkt": ":",
}
_PUNCTUATION_RE = re.compile(
    r"[\s,.;:!?]*\b(" + "|".join(_PUNCTUATION_COMMANDS) + r")\b" + _TRAILING_PUNCT + r"\s*",
    re.IGNORECASE,
)


def _apply_punctuation_commands(text: str) -> str:
    # split() mit Gruppe liefert [Text, Befehl, Text, Befehl, Text ...]
    parts = _PUNCTUATION_RE.split(text)
    result = parts[0]
    for command, rest in zip(parts[1::2], parts[2::2]):
        char = _PUNCTUATION_COMMANDS[command.lower()]
        if char in ".!?" and rest:
            rest = rest[0].upper() + rest[1:]
        result += char + (" " if rest else "") + rest
    return result


def continue_sentence(previous: str | None, text: str) -> str:
    """Endete das vorige Haeppchen mit einem Satzende (z. B. ein allein
    gesprochenes "Punkt"), beginnt dieses gross."""
    if previous and previous.rstrip()[-1:] in (".", "!", "?") and text[:1].islower():
        return text[0].upper() + text[1:]
    return text


# Satzzeichen, die die Erkennung selbst setzt. Zwischen zwei Ziffern bleiben sie
# stehen ("1.000", "14:30"). Kommas bleiben immer: Parakeet macht aus einem
# gesagten "Komma" selbst schon ein "," (das Wort kommt nie an) - von seinen
# eigenen Kommas ist das nicht zu unterscheiden. Gesagte "Punkt", "Fragezeichen"
# und "Ausrufezeichen" kommen dagegen als Wort an (mit Hedda-TTS geprueft).
_AUTO_PUNCT_RE = re.compile(r"(?<!\d)[.;:!?…]+|[.;:!?…]+(?!\d)")
PUNCTUATION_CHARS = ".,;:!?"


def strip_auto_punctuation(text: str) -> str:
    """Entfernt die Satzzeichen der Erkennung ausser Kommas. Parakeet und
    Whisper setzen gern an jede Sprechpause einen Punkt - wer sie selbst
    diktiert, bekaeme sonst doppelte."""
    text = _AUTO_PUNCT_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip(" \t")


def apply_voice_commands(text: str, punctuation: bool = False) -> str | None:
    """Setzt gesprochene Befehle um. Jedes Haeppchen landet ohnehin in einer
    eigenen Zeile - ein Umbruch am Anfang oder Ende eines Haeppchens ist also
    schon da und wird nicht doppelt gesetzt. Rueckgabe "" steht fuer eine
    Leerzeile ("Neuer Absatz" allein), None fuer "nichts ausgeben".
    punctuation=True heisst: Satzzeichen NUR per Sprache - die der Erkennung
    fallen weg, "Komma", "Punkt" ... werden zum Zeichen."""
    if punctuation:
        text = _apply_punctuation_commands(strip_auto_punctuation(text))
    text = _PARAGRAPH_RE.sub("\n\n", text)
    text = _LINE_RE.sub("\n", text)

    lines = [line.strip() for line in text.split("\n")]
    if lines and lines[0] == "":
        lines.pop(0)
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return None
    return "\n".join(lines)
