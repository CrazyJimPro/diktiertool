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

Einen anderen Ordner oder eine eigene Datei pro Aufnahme stellst du in den
[Einstellungen](#einstellungen) ein.

## Update

Beim Start prüft das Tool im Hintergrund, ob ein neueres Release existiert. Ist eines
verfügbar, erscheint neben der Versionsnummer im Header ein Hinweis-Badge – ein Klick
darauf öffnet die Release-Seite. Dort die neue `DiktiertoolSetup.exe` herunterladen und
ausführen; sie aktualisiert die vorhandene Installation, ohne Python oder das
Spracherkennungsmodell erneut zu laden.

## Deinstallation

Über "Apps & Features" (oder den Eintrag "Deinstallieren" im Startmenü). Entfernt den
kompletten Programmordner samt portablem Python und Modell-Zwischenspeicher, außerdem die
Einstellungen unter `%APPDATA%\Diktiertool`.
**Die Diktate unter `Dokumente\Diktiertool` (oder im selbst gewählten Ordner) bleiben
erhalten.**

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
bleibt ausschließlich auf diesem Rechner. Ordner und Aufteilung lassen sich in den
[Einstellungen](#einstellungen) ändern.

---

# Für beide Plattformen

## Knöpfe unter dem Text

- **Kopieren:** kopiert den gesamten Text im Fenster in die Zwischenablage, mit allen
  Absätzen. Danach z. B. in eine Mail oder ein Word-Dokument einfügen (Strg+V).
- **Leeren:** leert nur die Anzeige im Fenster. In der Datei bleibt alles stehen.
- **Ordner öffnen:** öffnet den Ordner, in dem `diktat.txt` liegt (unter Windows
  `Dokumente\Diktiertool`, unter Linux den Projektordner – oder den in den Einstellungen
  gewählten).
- **Audiodatei …:** transkribiert eine fertige Aufnahme, siehe nächster Abschnitt.

## Audiodateien transkribieren

Für Sprachnachrichten, Diktiergerät-Aufnahmen oder Mitschnitte, die schon als Datei
vorliegen. Unterstützt werden mp3, m4a, wav, ogg, opus, flac, aac, wma sowie der Ton aus
mp4- und webm-Videos.

1. Auf **„Audiodatei …“** klicken und eine oder mehrere Dateien auswählen. Alternativ die
   Dateien einfach aus dem Explorer ins Fenster ziehen. Das Fenster zeigt dann „Audiodatei
   loslassen zum Transkribieren“.
2. Die Statuszeile zeigt den Fortschritt in Prozent. Der erkannte Text erscheint
   absatzweise im Fenster. Eine Stunde Aufnahme braucht mit dem Modell small je nach
   Rechner etwa 5 bis 15 Minuten, mit medium oder large-v3-turbo deutlich länger.
3. Das Ergebnis landet als Textdatei **neben der Audiodatei**: aus `Sprachnachricht.m4a`
   wird `Sprachnachricht.txt`. Gibt es die schon, heißt die neue
   `Sprachnachricht (2).txt`, überschrieben wird nie etwas. Lässt sich neben der Audiodatei
   nicht schreiben (z. B. CD oder schreibgeschützter Ordner), landet sie im Ausgabeordner.
4. Fertig steht in der Statuszeile, wo die Datei gespeichert ist.

Ein neuer Absatz beginnt nach einer Sprechpause von zwei Sekunden oder bei gesprochenem
„neuer Absatz“. Sprache, eigene Wörter und Satzzeichen per Sprache aus den
Einstellungen gelten auch hier.

**Abbrechen:** Während der Transkription heißt der Knopf „Abbrechen“. Der bis dahin
erkannte Text bleibt in der Datei erhalten, am Ende steht „--- abgebrochen bei … % ---“.
Bei mehreren Dateien werden die restlichen übersprungen.

Während einer Transkription ist „Start“ gesperrt, während einer Aufnahme der Knopf
„Audiodatei …“. Beides gleichzeitig geht nicht.

## Einstellungen

Das Zahnrad oben rechts (neben dem Design-Knopf) öffnet die Einstellungen. Jede Änderung
wird sofort gespeichert, „Fertig“ führt zurück zur Aufnahme.

### Spracherkennungsmodell wechseln

1. Unter „Spracherkennungsmodell“ eines auswählen:
   - **small:** schnell, die Vorgabe. Reicht für deutliches Diktieren meist aus.
   - **medium:** genauer, braucht aber spürbar länger, bis der Text erscheint.
   - **large-v3-turbo:** am genauesten, braucht am meisten Arbeitsspeicher (rund 2 GB frei).
2. Das Modell lädt sofort neu. Beim ersten Mal wird es heruntergeladen (medium ca. 1,5 GB,
   large-v3-turbo ca. 1,6 GB), das kann einige Minuten dauern. Bis dahin ist „Start“
   gesperrt.
3. Danach steht in der Statuszeile „Bereit (Modell …)“.

Während einer Aufnahme lässt sich das Modell nicht wechseln, erst nach „Stop“.

### Sprache

„Deutsch“ (Vorgabe), „Englisch“ oder „Automatisch erkennen“. Bei „Automatisch“ bestimmt
die Erkennung die Sprache für jeden Satz neu. Bei kurzen Sätzen liegt sie dabei
gelegentlich daneben. Wer nur eine Sprache spricht, stellt sie deshalb besser fest ein.
Die Änderung gilt sofort, auch mitten in einer Aufnahme.

### Ausgabeordner

1. Auf **„Ändern …“** klicken und einen Ordner auswählen.
2. Ab der nächsten Aufnahme landet der Text dort.
3. **„Standard“** führt zurück zum ursprünglichen Ordner (der Knopf erscheint nur, wenn ein
   eigener Ordner gewählt ist).

Ist der gewählte Ordner beim Start einer Aufnahme nicht erreichbar (USB-Stick abgezogen,
Netzlaufwerk getrennt), schreibt das Tool in den Standardordner und sagt das in der
Statuszeile.

### Für jede Aufnahme eine eigene Datei

Ist der Haken gesetzt, bekommt jede Aufnahme eine eigene Datei mit Datum und Uhrzeit im
Namen, z. B. `diktat_2026-10-10_14-30.txt`, statt alles nacheinander in `diktat.txt` zu
schreiben. Welche Datei gerade beschrieben wird, steht beim Start in der Statuszeile.

### Satzzeichen per Sprache

Ist der Haken gesetzt, werden „Komma“, „Punkt“, „Fragezeichen“, „Ausrufezeichen“ und
„Doppelpunkt“ zum jeweiligen Zeichen. Vorgabe ist aus: Die Erkennung setzt Satzzeichen
ohnehin selbst, und „der Punkt ist …“ würde sonst zu „der. Ist …“.

### Eigene Wörter

Namen und Fachbegriffe, die sonst falsch geschrieben werden: einen Begriff pro Zeile
eintragen (Komma geht auch). Sie gelten ab dem nächsten Satz. Am besten wirken wenige
gezielte Wörter, eine lange Liste verwässert den Effekt.

### Wo die Einstellungen gespeichert werden

- Windows: `%APPDATA%\Diktiertool\settings.json`
- Linux: `~/.config/diktiertool/settings.json`

## Absätze per Sprache

Beim Diktieren einfach mitsprechen:

| Gesagt | Ergebnis |
|---|---|
| „neuer Absatz“ | Leerzeile, danach geht es in einem neuen Absatz weiter |
| „neue Zeile“ | Zeilenumbruch |

Satzzeichen per Sprache („Komma“, „Punkt“ …) sind ausgeschaltet und lassen sich in den
[Einstellungen](#satzzeichen-per-sprache) einschalten.

## Zuletzt benutztes Mikrofon

Das Tool merkt sich das Mikrofon, mit dem zuletzt eine Aufnahme gestartet wurde, und wählt
es beim nächsten Start wieder vor. Ist es gerade nicht angeschlossen, steht wie bisher
„Standard-Mikrofon“ in der Liste. Gespeichert wird das mit den übrigen
[Einstellungen](#wo-die-einstellungen-gespeichert-werden).

## Wenn etwas nicht klappt

- **Das falsche Mikrofon ist vorgewählt:** einfach in der Liste umstellen, beim nächsten
  „Start“ merkt sich das Tool die neue Wahl.
- **Das Tool startet nicht mehr, nachdem an der Einstellungsdatei herumgebastelt wurde:**
  Das sollte nicht passieren (eine kaputte Datei wird ignoriert). Falls doch, die Datei
  `settings.json` (Pfad siehe oben) löschen und neu starten.
- **Nach einem Modellwechsel steht „Modell … ließ sich nicht laden“:** Meist ist der
  Download abgebrochen (keine Internetverbindung, zu wenig Speicherplatz). Das Tool arbeitet
  dann mit dem vorherigen Modell weiter. Später in den Einstellungen erneut auswählen.
- **Der Text landet nicht im gewählten Ordner:** Die Statuszeile nennt beim Start den
  Grund und den Ordner, in den stattdessen geschrieben wird. Ordner in den Einstellungen
  neu wählen.
- **„keine lesbare Audiodatei“:** Die Datei ist keine Audiodatei, beschädigt oder ein
  Format mit Kopierschutz (z. B. gekaufte Hörbücher). In einem anderen Programm
  abspielbar? Dann als mp3 oder wav exportieren und die exportierte Datei nehmen.
- **Die Transkription einer Datei zieht sich:** Lange Aufnahmen brauchen Zeit, die
  Prozentanzeige läuft dabei weiter. Das kleinere Modell (small) ist deutlich schneller.
- **Bei langen Stillen in einer Aufnahme erscheinen erfundene Sätze:** Siehe
  „Bekannte Eigenheiten“ unten. Die bekannten filtert das Tool heraus.
- **„Kopieren“ tut scheinbar nichts:** Der Knopf ist gesperrt, solange im Fenster kein Text
  steht. Nach dem Klick zeigt er kurz „Kopiert ✓“.

## Bekannte Eigenheiten

- Das Tool läuft immer nur einmal. Ein weiterer Start (z. B. ein zweiter Doppelklick auf
  das Symbol) öffnet kein zweites Fenster, sondern holt das vorhandene nach vorne, auch
  wenn es minimiert war.
- Text erscheint satzweise mit ein paar Sekunden Verzögerung (Sprechpause + Rechenzeit),
  nicht Wort-für-Wort live. Das ist eine bewusste Entscheidung für bessere Genauigkeit.
- Bricht die Mikrofon-Verbindung mitten in der Aufnahme ab (z.B. Bluetooth getrennt), zeigt
  das Tool eine Fehlermeldung und stoppt sauber. Es verbindet sich nicht automatisch neu –
  Gerät neu auswählen und "Start" erneut drücken.
- Bei reinem Hintergrundgeräusch (ohne echte Sprache) erfindet Whisper gelegentlich kurze
  Textschnipsel, meist Abspann-Sätze aus Fernsehuntertiteln („Untertitel im Auftrag des
  ZDF“, „Vielen Dank fürs Zuschauen“). Die bekannten Sätze filtert das Tool heraus, ebenso
  Wiederholungsschleifen („und dann und dann und dann …“). Ganz verhindern lässt sich das
  nicht. Taucht ein neuer Phantomsatz öfter auf, kann er in `text_postprocess.py` in die
  Liste `_PHANTOM_PATTERNS` aufgenommen werden.

## Neue Version veröffentlichen

Die Versionsnummer steht an zwei Stellen und muss übereinstimmen, sonst bricht der
Build-Workflow ab:

1. `VERSION` in `config.py`
2. die Vorgabe `MyAppVersion` in `installscript/windows/setup.iss`

Danach einen `v<version>`-Tag pushen. Der Workflow
`.github/workflows/build-windows-installer.yml` baut daraufhin `DiktiertoolSetup.exe` und
hängt sie als Asset an das Release.
