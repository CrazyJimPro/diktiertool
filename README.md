# Diktiertool

Ein einfaches, lokales Diktiergerät: spricht ins Mikrofon (auch Bluetooth-Headsets/AirPods),
der erkannte Text erscheint live in einem kleinen Fenster und wird laufend in `diktat.txt`
gespeichert. Die Spracherkennung läuft komplett offline auf diesem Rechner (faster-whisper) –
es wird kein Audio an einen Server geschickt, und `diktat.txt` bleibt lokal (siehe unten).

Läuft unter **Windows** und **Linux**.

Die Oberfläche (`web/index.html`, `style.css`, `app.js`) ist echtes HTML/CSS/JS, angezeigt in
einem nativen Fenster über [pywebview](https://pywebview.flowrl.com/) – nicht mehr
customtkinter. Grund: nur so sind die weichen organischen Formen, Verlaufsfarben und
Animationen des aktuellen Designs technisch möglich. `gui.py` bindet Python (Mikrofon,
Whisper, Datei-Schreiben) per `js_api`/`evaluate_js` an die Oberfläche an. Welche
Browser-Engine das Fenster füllt, entscheidet pywebview selbst: unter Windows WebView2
(Chromium, in Windows 11 enthalten), unter Linux GTK/WebKit2.

---

# Windows

## Installation

1. Auf der [Releases-Seite](https://github.com/CrazyJimPro/diktiertool/releases) die Datei
   `DiktiertoolSetup.exe` herunterladen.
2. Doppelklick, dem Assistenten folgen. Das war's.

Der Installer braucht **keine Administratorrechte** und installiert nach
`%LOCALAPPDATA%\Diktiertool`. Er richtet alles Nötige selbst ein:

- ein portables Python (~11 MB, wird nur in den Programmordner entpackt und trägt sich
  nirgends im System ein – ein eventuell schon vorhandenes Python bleibt unangetastet)
- die Abhängigkeiten `faster-whisper`, `sounddevice`, `numpy`, `pywebview`
- die WebView2-Runtime, falls sie fehlt (unter Windows 11 normalerweise vorhanden)
- eine Verknüpfung auf dem Desktop und Einträge im Startmenü

Weil der Installer den Programmcode bei der Installation von GitHub lädt, ist dabei eine
Internetverbindung nötig. Dauert insgesamt ein paar Minuten, das meiste davon `pip`.

**Erster Start:** Lädt einmalig das Spracherkennungsmodell (~500 MB), das kann einige
Minuten dauern. Der Status im Fenster zeigt es an, der Start-Knopf ist bis dahin gesperrt.
Danach liegt das Modell dauerhaft lokal und lädt in Sekunden.

Beim Start ohne Windows-Anmeldung an Microsoft, ohne Konto, ohne irgendetwas: das Tool
telefoniert nur für den Modell-Download und den Update-Check nach Hause, sonst nie.

## Benutzung

Doppelklick auf das Desktop-Symbol – es startet ohne Konsolenfenster. Mikrofon aus der
Liste wählen, auf "Start" klicken, sprechen, mit "Stop" beenden.

Klemmt etwas, gibt es im Startmenü den Eintrag **"Diktiertool starten (mit Meldungen)"**:
derselbe Start, aber mit sichtbarer Konsole, in der Fehlermeldungen stehen bleiben.

## Wo landet der Text?

In `Dokumente\Diktiertool\diktat.txt` – nicht im Programmordner. Zwei Gründe: dort sucht
man seine Diktate, und die Deinstallation entfernt den Programmordner vollständig, die
Diktate aber ausdrücklich nicht.

## Update

Beim Start prüft das Tool im Hintergrund, ob ein neueres Release existiert. Ist eines
verfügbar, erscheint neben der Versionsnummer im Header ein Hinweis-Badge – ein Klick
darauf öffnet die Release-Seite. Dort die neue `DiktiertoolSetup.exe` herunterladen und
ausführen; sie aktualisiert die vorhandene Installation, ohne Python oder das
Spracherkennungsmodell erneut zu laden.

## Deinstallation

Über "Apps & Features" (oder den Eintrag "Deinstallieren" im Startmenü). Entfernt den
kompletten Programmordner samt portablem Python und Modell-Zwischenspeicher.
**Die Diktate unter `Dokumente\Diktiertool` bleiben erhalten.**

## Bekannte Eigenheiten unter Windows

- In der Mikrofonliste erscheinen nur WASAPI-Geräte. Windows meldet jedes Mikrofon sonst
  einmal pro Schnittstelle (MME, DirectSound, WASAPI, WDM-KS) – ein einziges Headset stünde
  bis zu sechsmal in der Liste, unter MME zusätzlich mit nach 31 Zeichen abgeschnittenem
  Namen.
- WASAPI läuft im Shared Mode mit dem Mischformat des Geräts (meist 48 kHz) und lehnt die
  von Whisper benötigten 16 kHz sonst rundheraus ab; die Abtastratenwandlung von PortAudio
  wird deshalb eingeschaltet (`auto_convert`).

---

# Linux

## Voraussetzungen

- Python 3.12 und die System-Pakete `python3-venv`, `libportaudio2`, `python3-gi`,
  `python3-gi-cairo`, `gir1.2-gtk-3.0` und `gir1.2-webkit2-4.1` (alle werden von
  `setup.sh` geprüft, falls etwas fehlt zeigt es den passenden `apt install`-Befehl)
- Internetverbindung nur für den einmaligen Modell-Download beim ersten Start

## Installation auf einem neuen Rechner

`installscript/bootstrap.sh` einmalig auf den neuen Rechner kopieren und ausführen:

```
bash bootstrap.sh
```

Das Skript klont das Repo nach `~/diktiertool` (überschreibbar per `DIKTIERTOOL_DIR=...`)
und führt anschließend `./setup.sh` aus.

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

## Update

Beim Start prüft das Tool im Hintergrund, ob eine neuere Version released wurde. Ist eine
verfügbar, erscheint neben der Versionsnummer im Header ein Hinweis-Badge, z. B. "Update
verfügbar: v1.1.0" – ein Klick darauf öffnet die passende Release-Seite auf GitHub. Ohne
Netz bleibt der Badge einfach weg, kein Fehler, kein blockierter Start.

Zum Aktualisieren:

```
cd ~/diktiertool   # oder wo auch immer installiert
git pull
./setup.sh
```

`./setup.sh` danach nicht weglassen, auch wenn es manchmal nur `git pull` bräuchte – es
prüft zusätzlich auf neue System-Pakete/Abhängigkeiten und richtet sie bei Bedarf ein, ist
aber schnell durchgelaufen, wenn sich nichts geändert hat. Zeigt es fehlende Pakete an, den
vorgeschlagenen `sudo apt install ...`-Befehl ausführen und `./setup.sh` erneut starten.
Danach wie gewohnt `./start.sh` oder über die Desktop-Verknüpfung starten.

## Ausgabe

Erkannter Text landet fortlaufend in `diktat.txt` im Projektordner, jede Sitzung mit einem
Datum/Uhrzeit-Trenner. Diese Datei ist bewusst nicht Teil von Git (`.gitignore`) – sie
bleibt ausschließlich auf diesem Rechner.

---

# Für beide Plattformen

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

## Neue Version veröffentlichen

Die Versionsnummer steht an zwei Stellen und muss übereinstimmen, sonst bricht der
Build-Workflow ab:

1. `VERSION` in `config.py`
2. die Vorgabe `MyAppVersion` in `installscript/windows/setup.iss`

Danach einen `v<version>`-Tag pushen. Der Workflow
`.github/workflows/build-windows-installer.yml` baut daraufhin `DiktiertoolSetup.exe` und
hängt sie als Asset an das Release.
