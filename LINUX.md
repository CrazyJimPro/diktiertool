# Diktiertool unter Linux

Anleitung für die Installation, Benutzung, Updates und Deinstallation unter Linux. Was auf
Windows und Linux gleich ist (Knöpfe, Audiodateien transkribieren, Diktieren per Taste,
Einstellungen, Fehlersuche …), steht in der [allgemeinen Anleitung](README.md). Die
Windows-Anleitung gibt es unter [WINDOWS.md](WINDOWS.md).

- [Voraussetzungen](#voraussetzungen)
- [Installation auf einem neuen Rechner](#installation-auf-einem-neuen-rechner)
- [Einrichtung (einmalig)](#einrichtung-einmalig)
- [Benutzung (jedes Mal)](#benutzung-jedes-mal)
- [Desktop-Verknüpfung](#desktop-verknüpfung)
- [Update](#update)
- [Ausgabe](#ausgabe)
- [Deinstallation](#deinstallation)

---

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
vorgeschlagenen `sudo apt update && sudo apt install ...`-Befehl ausführen und `./setup.sh`
erneut starten.
Danach wie gewohnt `./start.sh` oder über die Desktop-Verknüpfung starten.

## Ausgabe

Erkannter Text landet fortlaufend in `diktat.txt` im Projektordner, jede Sitzung mit einem
Datum/Uhrzeit-Trenner. Diese Datei ist bewusst nicht Teil von Git (`.gitignore`) – sie
bleibt ausschließlich auf diesem Rechner. Ordner und Aufteilung lassen sich in den
[Einstellungen](README.md#einstellungen) ändern.

## Deinstallation

```
./uninstall.sh
```

Beendet ein laufendes Diktiertool, entfernt Menü-/Desktop-Verknüpfung, Einstellungen
(`~/.config/diktiertool`), Diagnose-Log (`~/.local/state/diktiertool`) und die
heruntergeladenen Spracherkennungsmodelle (Whisper- und Parakeet-Anteil im geteilten
`~/.cache/huggingface`, dort gezielt per Namensmuster statt den ganzen Cache-Ordner zu
leeren). Zeigt am Ende den Befehl, um danach auch noch den Projektordner samt virtueller
Umgebung zu löschen (`rm -rf ...`) – das kann das Skript nicht selbst, solange es darin
noch läuft. Diktate bleiben in jedem Fall erhalten.
