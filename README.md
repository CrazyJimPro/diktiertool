# Diktiertool

Ein einfaches, lokales Diktiergerät: spricht ins Mikrofon (auch Bluetooth-Headsets/AirPods),
der erkannte Text erscheint live in einem kleinen Fenster und wird laufend in `diktat.txt`
gespeichert. Die Spracherkennung läuft komplett offline auf diesem Rechner (faster-whisper) –
es wird kein Audio an einen Server geschickt, und `diktat.txt` bleibt lokal (siehe unten).

Die Oberfläche (`web/index.html`, `style.css`, `app.js`) ist echtes HTML/CSS/JS, angezeigt in
einem nativen Fenster über [pywebview](https://pywebview.flowrl.com/) (GTK/WebKit2-Backend) –
nicht mehr customtkinter. Grund: nur so sind die weichen organischen Formen, Verlaufsfarben
und Animationen des aktuellen Designs technisch möglich. `gui.py` bindet Python (Mikrofon,
Whisper, Datei-Schreiben) per `js_api`/`evaluate_js` an die Oberfläche an.

## Voraussetzungen

- Linux mit Python 3.12 und den System-Paketen `python3-venv`, `libportaudio2`,
  `python3-gi`, `python3-gi-cairo`, `gir1.2-gtk-3.0` und `gir1.2-webkit2-4.1` (GUI läuft
  über pywebview mit GTK/WebKit2-Backend, siehe unten; alle Pakete werden von `setup.sh`
  geprüft, falls etwas fehlt zeigt es den passenden `apt install`-Befehl)
- Internetverbindung nur für den einmaligen Modell-Download beim ersten Start

## Installation auf einem neuen Rechner

Das Repo ist privat, daher gibt es keinen anonymen `curl | bash`-Oneliner. Stattdessen:

1. `installscript/bootstrap.sh` einmalig auf den neuen Rechner kopieren (Inhalt einfügen,
   USB-Stick, o. ä.).
2. Dort ausführen: `bash bootstrap.sh`

Das Skript installiert bei Bedarf die GitHub CLI (`gh`) und klont danach das Repo nach
`~/diktiertool` (überschreibbar per `DIKTIERTOOL_DIR=...`), bevor es automatisch
`./setup.sh` ausführt. Bist du auf diesem Rechner noch nicht bei GitHub angemeldet, fragt
es das zwischendurch interaktiv ab (`gh auth login --web`, einmalig pro Rechner):

- "What account do you want to log into?" → **GitHub.com**
- "Preferred protocol for Git operations?" → **HTTPS** (empfohlen – kein separates
  SSH-Key-Management nötig)
- "Authenticate Git with your GitHub credentials?" → **Yes**
- "How would you like to authenticate?" → **Login with a web browser**
- Terminal zeigt einen einmaligen Code → Browser öffnet sich (oder Link manuell öffnen) →
  Code eingeben, mit dem GitHub-Account bestätigen (+2FA falls aktiv)

Ist das Repo auf dem Rechner schon vorhanden (wie hier), reicht der nächste Schritt allein.

## Einrichtung (einmalig)

```
./setup.sh
```

Legt eine lokale virtuelle Python-Umgebung an, installiert alle Abhängigkeiten und richtet
dabei automatisch die Desktop-Verknüpfung ein (siehe unten).

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

## Desktop-Verknüpfung

Wird automatisch als letzter Schritt von `setup.sh` eingerichtet – gemeint ist nur die
Verknüpfung zum Starten, nicht das Tool selbst. Legt ein Icon im Anwendungsmenü und auf
dem Desktop an: ein Doppelklick startet das Tool genau wie `./start.sh`, kein Terminal
nötig. Am Verhalten des Tools ändert das nichts – es läuft weiterhin nur, solange das
Fenster offen ist (kein Hintergrunddienst, kein Autostart, kein Tray-Icon), und die
Aufnahme startet erst nach Klick auf "Start" im Fenster. Nutzt `xdg-user-dir DESKTOP`,
funktioniert also auch bei nicht-englischer Locale (z. B. `~/Schreibtisch`). Zeigt
Nautilus beim ersten Doppelklick auf dem Desktop-Icon nur eine Warnung: einmal
rechtsklicken → "Start erlauben".

Bei Bedarf einzeln erneut ausführbar (z. B. falls das Icon versehentlich gelöscht wurde):

```
./install-desktop-entry.sh
```

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
- Beim Start prüft das Tool im Hintergrund per `gh` (nicht der rohen GitHub-API, da das
  Repo privat ist), ob eine neuere Version released wurde, und zeigt dann im Header einen
  Hinweis-Badge (Klick öffnet die Release-Seite). Ist `gh` nicht installiert oder nicht
  angemeldet, bleibt der Badge einfach weg – kein Fehler, kein blockierter Start.

## Modellgröße ändern

In `config.py` steht `MODEL_SIZE = "small"`. Für höhere Genauigkeit (aber langsamer)
kann das auf `"medium"` geändert werden – lädt beim nächsten Start einmalig neu.
