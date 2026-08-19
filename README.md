# Diktiertool

Ein einfaches, lokales Diktiergerät: spricht ins Mikrofon (auch Bluetooth-Headsets/AirPods),
der erkannte Text erscheint live in einem kleinen Fenster und wird laufend in `diktat.txt`
gespeichert. Die Spracherkennung läuft komplett offline auf diesem Rechner (faster-whisper) –
es wird kein Audio an einen Server geschickt, und `diktat.txt` bleibt lokal (siehe unten).

## Voraussetzungen

- Linux mit Python 3.12 und den System-Paketen `python3-tk`, `python3-venv` und
  `libportaudio2` (werden von `setup.sh` geprüft; falls etwas fehlt, zeigt es den
  passenden `apt install`-Befehl)
- Internetverbindung nur für den einmaligen Modell-Download beim ersten Start

## Installation auf einem neuen Rechner

Das Repo ist privat, daher gibt es keinen anonymen `curl | bash`-Oneliner. Stattdessen:

1. `installscript/bootstrap.sh` einmalig auf den neuen Rechner kopieren (Inhalt einfügen,
   USB-Stick, o. ä.).
2. Dort ausführen: `bash bootstrap.sh`

Das Skript installiert bei Bedarf die GitHub CLI (`gh`), meldet dich interaktiv bei GitHub
an (`gh auth login --web`, einmalig pro Rechner), klont das Repo nach `~/diktiertool`
(überschreibbar per `DIKTIERTOOL_DIR=...`) und führt danach automatisch `./setup.sh` aus.

Ist das Repo auf dem Rechner schon vorhanden (wie hier), reicht der nächste Schritt allein.

## Einrichtung (einmalig)

```
./setup.sh
```

Legt eine lokale virtuelle Python-Umgebung an und installiert alle Abhängigkeiten.

## Benutzung (jedes Mal)

```
./start.sh
```

Öffnet das Diktiertool-Fenster. Mikrofon aus der Liste wählen (bei Bluetooth-Geräten ggf.
vorher "Aktualisieren" drücken, damit sie auftauchen), auf "Start" klicken, sprechen, mit
"Stop" beenden.

**Erster Start:** Lädt einmalig das Spracherkennungsmodell (~500MB), das kann ein paar
Minuten dauern. Der Status zeigt das an, der Start-Button ist bis dahin gesperrt. Danach
ist das Modell dauerhaft lokal zwischengespeichert und lädt beim nächsten Mal in Sekunden.

## Ausgabe

Erkannter Text landet fortlaufend in `diktat.txt` im Projektordner, jede Sitzung mit einem
Datum/Uhrzeit-Trenner. Diese Datei ist bewusst nicht Teil von Git (`.gitignore`) – sie bleibt
ausschließlich auf diesem Rechner.

## Bekannte Eigenheiten

- Text erscheint satzweise mit ein paar Sekunden Verzögerung (Sprechpause + Rechenzeit),
  nicht Wort-für-Wort live. Das ist eine bewusste Entscheidung für bessere Genauigkeit.
- Bricht die Mikrofon-Verbindung mitten in der Aufnahme ab (z.B. Bluetooth getrennt), zeigt
  das Tool eine Fehlermeldung und stoppt sauber. Es verbindet sich nicht automatisch neu –
  Gerät neu auswählen und "Start" erneut drücken.
- Bei reinem Hintergrundgeräusch (ohne echte Sprache) kann die Erkennung gelegentlich kurze,
  erfundene Textschnipsel einfügen (bekanntes Whisper-Verhalten bei Stille).

## Modellgröße ändern

In `config.py` steht `MODEL_SIZE = "small"`. Für höhere Genauigkeit (aber langsamer)
kann das auf `"medium"` geändert werden – lädt beim nächsten Start einmalig neu.
