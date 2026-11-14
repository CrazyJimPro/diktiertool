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


# Steht ein Artikel davor ("einen Punkt", "kein Fragezeichen", "der Punkt ist"),
# ist das Wort gemeint und kein Befehl.
_ARTICLE_BEFORE_RE = re.compile(
    r"\b(ein|einen|einem|eines|kein|keinen|keinem|keines|der|den|dem|des|das|"
    r"dieser|diesen|diesem|dieses|jeder|jeden|jedem|welcher|welchen|welchem|zwei|drei|vier)"
    r"[\s,]*$",
    re.IGNORECASE,
)


def _apply_punctuation_commands(text: str) -> str:
    result = ""
    pos = 0
    capitalize = False
    for match in _PUNCTUATION_RE.finditer(text):
        if _ARTICLE_BEFORE_RE.search(text[:match.start()]):
            continue  # bleibt als Wort stehen
        before = text[pos:match.start()]
        if capitalize and before:
            before = before[0].upper() + before[1:]
        char = _PUNCTUATION_COMMANDS[match.group(1).lower()]
        result += before + char
        pos = match.end()
        if pos < len(text):
            result += " "
        capitalize = char in ".!?"
    rest = text[pos:]
    if capitalize and rest:
        rest = rest[0].upper() + rest[1:]
    return result + rest


# Woerter, die mitten im Satz klein geschrieben werden. Die Erkennung bekommt
# jedes Haeppchen (bis zur naechsten Sprechpause) einzeln und haelt es fuer einen
# neuen Satz - also schreibt sie das erste Wort gross, auch wenn nur kurz
# ueberlegt wurde. Bewusst ohne "sie/ihr/ihnen" (Anrede "Sie") und ohne Woerter,
# die oft auch Hauptwort sind ("morgen", "essen"). Hauptwoerter kommen hier nie
# vor - die bleiben gross.
_LOWERCASE_WORDS = frozenset("""
der die das den dem des ein eine einen einem einer eines kein keine keinen keinem keiner keines
dieser diese dieses diesen diesem jeder jede jedes jeden jedem mein meine meinen meinem meiner
dein deine deinen deinem deiner sein seine seinen seinem seiner unser unsere unseren euer eure
welche welcher welches welchen welchem manche alle alles beide viele wenige einige mehrere
ich du er es wir mich mir dich dir ihn ihm uns euch sich man jemand niemand nichts etwas
was wer wen wem wo wie warum wieso weshalb wann woher wohin womit wofür worüber woran dass
und oder aber denn sondern weil da wenn falls ob obwohl obgleich als bevor nachdem während damit
sodass bis seit seitdem sobald solange indem ohne um statt sowie also dann daher deshalb deswegen
trotzdem jedoch doch sonst außerdem zwar entweder weder noch
in im ins an am ans auf aus bei beim mit nach von vom vor zu zum zur über unter neben zwischen
durch für gegen hinter wegen trotz
nicht auch nur schon jetzt gerade eben hier dort immer nie oft manchmal mal einfach halt ja nein
so sehr ganz gar wohl vielleicht eigentlich bitte genau selbst selber sogar erst bereits wieder
gleich heute gestern bald später vorher nachher hoffentlich leider natürlich klar okay irgendwie
irgendwo irgendwann etwa ungefähr fast kaum mehr weniger besser lieber gern gerne zuerst danach
dafür dagegen darauf darum davon dazu dabei dadurch daran darin weiter allerdings zusammen allein
ist sind war waren bin bist hat habe hast haben hatte hatten wird werden wurde würde würden
kann kannst können konnte könnte muss musst müssen sollte soll sollen will willst wollen möchte
möchtest darf dürfen mache machen macht gemacht sage sagen sagt gesagt gehe geht gehen gibt geben
gegeben sehe siehst sieht sehen gesehen schau schauen weiß wissen glaube glauben denke denken
meinst finde finden brauche brauchst braucht brauchen lass lassen komme kommt kommen warte
warten schreibe schreiben schreibt geschrieben setzt setzen gesetzt erwähne erwähnen überlegen
groß gross klein gut schlecht neu alt richtig falsch kurz lang schnell langsam wichtig schwer
leicht willkürlich automatisch selbstständig selbständig
""".split())
# Diese nie dazulernen - "Sie" als Anrede bleibt gross
_NEVER_LOWERCASE = frozenset("sie ihr ihre ihren ihrem ihrer ihres ihnen".split())
_WORD_RE = re.compile(r"[^\W\d_]+")


class SentenceCase:
    """Gross- und Kleinschreibung ueber Haeppchen hinweg, fuer "Satzzeichen nur
    per Sprache": Nur nach einem gesagten Punkt, Frage- oder Ausrufezeichen
    (oder am Anfang) geht es gross weiter. Sonst wird das erste Wort klein,
    wenn es kein Hauptwort ist - erkennbar an der Liste oben oder daran, dass
    die Erkennung es mitten im Satz schon einmal klein geschrieben hat."""

    def __init__(self):
        self.previous: str | None = None
        self._learned: set[str] = set()
        self._seen_capital: set[str] = set()

    def reset(self):
        """Neue Aufnahme: das erste Haeppchen beginnt einen Satz."""
        self.previous = None

    def observe(self, raw: str):
        """Lernt aus dem unbearbeiteten Text der Erkennung, welche Woerter sie
        mitten im Satz klein schreibt (erstes Wort und Satzanfaenge zaehlen nicht)."""
        for match in _WORD_RE.finditer(raw):
            before = raw[:match.start()].rstrip()
            if not before or before[-1] in ".!?:\n":
                continue
            word = match.group()
            key = word.casefold()
            if word[0].islower():
                if key not in _NEVER_LOWERCASE:
                    self._learned.add(key)
            else:
                self._seen_capital.add(key)

    def apply(self, text: str) -> str:
        self.previous = text = self._apply(self.previous, text)
        return text

    def _apply(self, previous: str | None, text: str) -> str:
        if not previous or previous.endswith("\n"):
            return text  # Satzanfang - so lassen, wie die Erkennung es schreibt
        if previous.rstrip()[-1:] in (".", "!", "?"):
            return text[0].upper() + text[1:] if text[:1].islower() else text
        match = _WORD_RE.match(text)
        if not match:
            return text  # beginnt z. B. mit einem allein gesagten "Komma"
        word = match.group()
        key = word.casefold()
        if text[match.end():match.end() + 1] == "-":
            return text  # "Groß- und Kleinschreibung": Teil eines Hauptworts
        if word[0].isupper() and not word.isupper() and (
            key in _LOWERCASE_WORDS or (key in self._learned and key not in self._seen_capital)
        ):
            return word[0].lower() + text[1:]
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


_replacement_cache: tuple | None = None


def _replacement_pattern(rules) -> tuple[re.Pattern, list[str]] | None:
    """Ein einziger regulaerer Ausdruck fuer alle Regeln, laengste zuerst - so
    gewinnt "Schreibtische Treibung" vor "Treibung", und was eine Regel
    eingesetzt hat, ersetzt keine zweite noch einmal."""
    global _replacement_cache
    key = tuple(tuple(r) for r in rules)
    if _replacement_cache is not None and _replacement_cache[0] == key:
        return _replacement_cache[1]
    ordered = sorted(((w, r) for w, r in key if w.strip()), key=lambda rule: -len(rule[0]))
    if not ordered:
        compiled = None
    else:
        parts = []
        for index, (wrong, _) in enumerate(ordered):
            # Zwischen den Woertern beliebig viel Leerraum, auch ein Komma der
            # Erkennung ("Schreibtische, Treibung")
            body = r",?\s+".join(re.escape(word) for word in wrong.split())
            start = r"(?<!\w)" if re.match(r"\w", wrong) else ""
            end = r"(?!\w)" if re.search(r"\w$", wrong) else ""
            parts.append(f"(?P<r{index}>{start}{body}{end})")
        compiled = (re.compile("|".join(parts), re.IGNORECASE), [r for _, r in ordered])
    _replacement_cache = (key, compiled)
    return compiled


def apply_replacements(text: str, rules) -> str | None:
    """Eigene Ersetzungen "falsch → richtig" auf den fertigen Text. Gross-/
    Kleinschreibung spielt beim Suchen keine Rolle. Stand das gefundene Wort
    gross (z. B. am Satzanfang), beginnt auch der Ersatz gross. Bleibt nach dem
    Ersetzen nichts uebrig, kommt None (nichts ausgeben)."""
    compiled = _replacement_pattern(rules) if rules and text else None
    if compiled is None:
        return text
    pattern, replacements = compiled
    removed = False

    def substitute(match):
        nonlocal removed
        right = replacements[int(match.lastgroup[1:])]
        if not right:
            removed = True
        elif right[:1].islower() and match.group()[:1].isupper():
            right = right[0].upper() + right[1:]
        return right

    original = text
    text = pattern.sub(substitute, text)
    if removed:
        # Ein leerer Ersatz ("äh →") hinterlaesst doppelte Leerzeichen und
        # verwaiste Kommas ("Äh, ich" -> ", ich")
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
        text = re.sub(r"(^|\n)[ \t,]+", r"\1", text)
        text = re.sub(r",[ \t]*([.;:!?]|$)", r"\1", text, flags=re.MULTILINE)
        text = "\n".join(line.strip(" \t") for line in text.split("\n"))
        if not re.search(r"\w", text):
            return None  # nur noch Satzzeichen uebrig ("Äh." -> ".")
        # Fiel das erste Wort weg, beginnt das naechste den Satz
        if original[:1].isupper() and text[:1].islower():
            text = text[0].upper() + text[1:]
    return text


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
