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

## Installation, Benutzung, Update, Deinstallation

| | |
| --- | --- |
| **Windows** | `DiktiertoolSetup.exe` von der [Releases-Seite](https://github.com/CrazyJimPro/diktiertool/releases) herunterladen und starten. Schritt für Schritt: [Anleitung für Windows](WINDOWS.md) |
| **Linux** | `installscript/bootstrap.sh` ausführen. Schritt für Schritt: [Anleitung für Linux](LINUX.md) |

Was auf beiden Systemen gleich ist – Bedienung, Einstellungen, Fehlersuche – steht hier auf
dieser Seite.

---

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

## Diktieren per Taste, direkt ins Programm

Statt im Diktiertool-Fenster auf „Start“ zu klicken, kannst du eine Taste festlegen, die
in jedem Programm funktioniert. Auf Wunsch tippt das Tool den erkannten Text direkt dort
ein, wo gerade der Cursor steht: in Word, im Browser, in einer Mail.

**Einrichten:**

1. Zahnrad → Reiter **Tastatur**.
2. Unter „Taste zum Diktieren“ eine Taste wählen: F8, F9, F10, F12, Pause oder Rollen.
   Am besten eine, die du sonst nie brauchst, denn sie kommt bei keinem anderen Programm
   mehr an, solange das Diktiertool läuft.
3. „Bedienung“ wählen:
   - **Drücken: Start, nochmal: Stopp**: einmal drücken, sprechen, nochmal drücken.
   - **Gedrückt halten zum Sprechen**: wie ein Funkgerät, Aufnahme nur solange die Taste
     unten ist.
4. Haken bei **„Text dort eintippen, wo der Cursor steht“**, wenn der Text direkt im
   anderen Programm landen soll.
5. Die Statuszeile zeigt dann z. B. „Bereit – F9 startet die Aufnahme“.

**Benutzen:**

1. Das Diktiertool läuft im Hintergrund (es darf minimiert sein).
2. Im Zielprogramm an die Stelle klicken, an die der Text soll.
3. Taste drücken (bzw. halten). Mit eingeschaltetem Signalton piept es hoch, und zwar
   genau dann, wenn das Mikrofon wirklich aufnimmt (je nach Gerät 0,1 bis 0,3 Sekunden
   nach dem Drücken, bei Bluetooth-Headsets auch länger).
4. Nach dem Piep sprechen. Der Text erscheint satzweise am Cursor, außerdem wie gewohnt im
   Fenster und in der Datei. Ohne Signalton kurz nach dem Drücken mit dem Sprechen warten.
5. Taste nochmal drücken (bzw. loslassen). Es piept tiefer.

Gut zu wissen:

- **„Neuer Absatz“ und „neue Zeile“ werden zu Enter.** In Chats und Messengern schickt
  Enter die Nachricht sofort ab. Dort also besser keine Absätze diktieren.
- Während das Tool tippt, nicht selbst tippen, sonst mischen sich die Zeichen.
- Steht der Cursor im Diktiertool-Fenster selbst, wird nicht zusätzlich getippt.
- **Programme, die als Administrator laufen** (z. B. manche Installationsprogramme oder
  eine Admin-Eingabeaufforderung): Dort kommt Windows-bedingt weder die Taste an noch der
  getippte Text, solange das Diktiertool selbst ohne Adminrechte läuft.
- **Linux:** Taste und Tippen funktionieren nur in einer X11-Sitzung, nicht unter Wayland.
  Die Taste wird dort außerdem nicht abgefangen, sondern kommt zusätzlich beim Programm an.

## Einstellungen

Das Zahnrad oben rechts (neben dem Design-Knopf) öffnet die Einstellungen. Sie sind auf
Reiter verteilt: **Erkennung** (Modell, Sprache, eigene Wörter, Ersetzungen, Satzzeichen), **Ausgabe**
(Ordner, eigene Datei pro Aufnahme), **Tastatur** (Taste zum Diktieren, Tippen am Cursor,
siehe oben) und **Diagnose**. Jede Änderung wird sofort gespeichert, „Fertig“ führt
zurück zur Aufnahme.

### Spracherkennungsmodell wechseln

1. Unter „Spracherkennungsmodell“ eines auswählen:
   - **small:** schnell, die Vorgabe. Reicht für deutliches Diktieren meist aus.
   - **medium:** genauer, braucht aber spürbar länger, bis der Text erscheint.
   - **large-v3-turbo:** am genauesten, braucht am meisten Arbeitsspeicher (rund 2 GB frei).
   - **Parakeet (nur Deutsch):** eine andere Erkennung, siehe unten. Sehr schnell.
2. Das Modell lädt sofort neu. Beim ersten Mal wird es heruntergeladen (medium ca. 1,5 GB,
   large-v3-turbo ca. 1,6 GB, Parakeet ca. 640 MB), das kann einige Minuten dauern. Bis
   dahin ist „Start“ gesperrt.
3. Danach steht in der Statuszeile „Bereit (Modell …)“.

Während einer Aufnahme oder Transkription lässt sich das Modell nicht wechseln, erst
danach.

### Parakeet statt Whisper

Die Modelle small, medium und large-v3-turbo sind alle „Whisper“ von OpenAI. Parakeet ist
eine ganz andere Spracherkennung, ein auf Deutsch trainiertes Modell.

- **Vorteile:** etwa fünfmal schneller als Whisper small (ein Satz in unter einer
  halben Sekunde, eine Stunde Audio in wenigen Minuten). Bei Stille oder Rauschen erfindet
  es keine Sätze. Satzzeichen und Großschreibung setzt es selbst (außer mit Haken bei
  [„Satzzeichen nur per Sprache“](#satzzeichen-per-sprache)).
- **Einschränkungen:** nur Deutsch. „Sprache“ und „Eigene Wörter“ gelten nicht und sind
  ausgegraut, solange Parakeet gewählt ist. Für Wörter, die Parakeet immer wieder falsch
  hört, gibt es die [Ersetzungen](#ersetzungen). Braucht etwas mehr Arbeitsspeicher (rund 1 GB,
  bei Audiodateien kurzzeitig mehr).
- Am besten einfach ausprobieren: Zwischen Whisper und Parakeet lässt sich jederzeit hin-
  und herschalten.

Parakeet stammt von [primeline/parakeet-primeline](https://huggingface.co/primeline/parakeet-primeline)
(deutscher Fine-Tune von primeline) auf Basis von NVIDIAs
[parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), hier in der
ONNX-Fassung [flozen1981/parakeet-primeline-onnx](https://huggingface.co/flozen1981/parakeet-primeline-onnx).
Lizenz: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Ausgeführt wird es mit
[sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx). Die Idee, Parakeet so einzubinden,
stammt aus [winidi/dictate](https://github.com/winidi/dictate).

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

Du hast die Wahl zwischen zwei Arten:

- **Ohne Haken (Vorgabe):** Die Erkennung setzt Punkt, Komma und Co. selbst. Das klappt
  meist gut, an Sprechpausen landet aber gern auch mitten im Satz ein Punkt.
- **Mit Haken bei „Satzzeichen nur per Sprache“:** Die Erkennung setzt keine eigenen
  Punkte, Frage- und Ausrufezeichen, Doppelpunkte und Semikolons mehr. Es erscheinen nur
  noch die, die du sagst: „Punkt“, „Fragezeichen“, „Ausrufezeichen“, „Doppelpunkt“ und
  „Komma“. Nach „Punkt“, „Fragezeichen“ und „Ausrufezeichen“ geht es mit einem
  Großbuchstaben weiter, auch wenn du dazwischen eine Pause machst. Zahlen wie „1.000“
  oder „14:30“ bleiben erhalten.
- **Großschreibung nach Denkpausen:** Das Tool gibt den Text in Häppchen bis zur nächsten
  Sprechpause an die Erkennung, und die hält jedes Häppchen für einen neuen Satz. Mit
  Haken wird deshalb das erste Wort eines Häppchens wieder klein, wenn davor kein
  „Punkt“, „Fragezeichen“ oder „Ausrufezeichen“ kam, etwa „und“, „weil“, „selbst“ oder
  „ich“. Hauptwörter bleiben groß. Das Tool kennt die häufigsten kleinen Wörter und lernt
  während des Diktats dazu, welche die Erkennung mitten im Satz klein schreibt. Ein
  seltenes Wort direkt nach einer Pause kann trotzdem einmal groß bleiben.
- **Kommas** setzt die Erkennung in beiden Fällen weiter selbst. Parakeet macht aus einem
  gesagten „Komma“ schon von sich aus ein Komma und setzt dazu eigene, etwa vor „dass“ –
  beides sieht im Ergebnis gleich aus und lässt sich nicht auseinanderhalten.

Der Haken gilt für beide Modelle (Whisper und Parakeet) und auch für Audiodateien. Steht
ein Artikel davor, bleibt das Wort stehen: „einen Punkt“, „kein Fragezeichen“, „der Punkt
ist …“ werden nicht zum Zeichen. Ohne Artikel („Punkt ist …“) wird es dagegen eins. Bei
„Komma“ geht das mit Parakeet nicht, weil es das Wort schon selbst zum Zeichen macht.

### Eigene Wörter

Namen und Fachbegriffe, die sonst falsch geschrieben werden: einen Begriff pro Zeile
eintragen (Komma geht auch). Sie gelten ab dem nächsten Satz. Am besten wirken wenige
gezielte Wörter, eine lange Liste verwässert den Effekt. Gilt nur für Whisper; bei
Parakeet helfen stattdessen die [Ersetzungen](#ersetzungen).

### Ersetzungen

Für Wörter, die die Erkennung immer wieder gleich falsch schreibt. Gilt für Whisper und
Parakeet, beim Diktieren und bei Audiodateien.

1. Im Reiter **Erkennung** in das Feld **„Ersetzungen“** klicken.
2. Eine Regel pro Zeile eintragen: links, was die Erkennung schreibt, rechts, was dastehen
   soll, dazwischen `->` (`=`, `=>` und `→` gehen auch). Beispiel:
   ```
   gross- und kleinen Schreibtische Treibung -> Groß- und Kleinschreibung
   Kuber Netis -> Kubernetes
   äh ->
   ```
3. Das Feld verlassen oder auf „Fertig“ klicken. Die Regeln gelten ab dem nächsten Satz.

Gut zu wissen:

- Groß- und Kleinschreibung links ist egal. Steht das gefundene Wort am Satzanfang groß,
  beginnt auch der Ersatz groß.
- Es werden nur ganze Wörter ersetzt: „Kuber Netis“ trifft nicht „Kuber Netisse“.
- Setzt die Erkennung zwischen die Wörter ein Komma („Schreibtische, Treibung“), greift die
  Regel trotzdem.
- Rechts leer lassen (`äh ->`) streicht das Wort ganz.
- Überschneiden sich Regeln, gewinnt die längere. Was eine Regel eingesetzt hat, ändert
  keine zweite mehr.
- Zeilen ohne Pfeil fallen beim Verlassen des Felds weg.

### Diagnose

Für die Fehlersuche, wenn Text fehlt oder falsch ankommt.

- **Log-Ordner öffnen:** Das Tool schreibt ein Protokoll mit einer Zeile pro erkanntem
  Stück: Dauer, Lautstärke, wie stark angehoben wurde, erkannte Sprache, Rechenzeit und
  was aus welchem Grund verworfen wurde (z. B. ein erfundener Abspann-Satz). **Der
  erkannte Text steht nie darin**, auch keine Dateinamen von Audiodateien. Das Protokoll
  kann bei Problemen also gefahrlos weitergegeben werden. Es bleibt klein (höchstens
  4 × 512 KB, ältere Teile werden überschrieben).
- **Nicht erkannte Aufnahmen aufheben:** Ist der Haken gesetzt, landen Stücke, aus denen
  kein Text wurde, als WAV im Unterordner `fehlaufnahmen` des Log-Ordners, nur die letzten 3.
  Anhören zeigt schnell, ob das Mikrofon überhaupt etwas Brauchbares geliefert hat. Die
  Vorgabe ist aus, denn es sind Tonaufnahmen. Haken wieder entfernen löscht sie.

Wo das liegt:
- Windows: `%LOCALAPPDATA%\Diktiertool\logs`
- Linux: `~/.local/state/diktiertool/logs`

Außerdem hebt das Tool leise Aufnahmen automatisch an, bevor sie erkannt werden (bis zum
30-Fachen). Das hilft bei Mikrofonen mit zu niedrigem Pegel.

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
[Einstellungen](#satzzeichen-per-sprache) einschalten – dann setzt die Erkennung keine
eigenen mehr.

## Zuletzt benutztes Mikrofon

Das Tool merkt sich das Mikrofon, mit dem zuletzt eine Aufnahme gestartet wurde, und wählt
es beim nächsten Start wieder vor. Ist es gerade nicht angeschlossen, steht wie bisher
„Standard-Mikrofon“ in der Liste. Gespeichert wird das mit den übrigen
[Einstellungen](#wo-die-einstellungen-gespeichert-werden).

## Wenn etwas nicht klappt

- **Die Taste tut nichts:** Läuft das Diktiertool? (Die Taste funktioniert nur, solange
  es geöffnet ist, minimiert reicht.) Lädt das Modell noch, sagt die Statuszeile das. Im
  Vordergrund ist ein Programm mit Adminrechten? Dann lässt Windows die Taste dort nicht
  durch, siehe „Diktieren per Taste“.
- **Eine andere Taste funktioniert plötzlich nicht mehr:** Das ist die im Reiter Tastatur
  gewählte. Das Diktiertool fängt sie ab. Dort eine andere wählen oder „Aus“.
- **Der Text wird nicht ins Programm getippt:** Haken „Text dort eintippen, wo der Cursor
  steht“ gesetzt? Stand der Cursor im Diktiertool selbst? Dort wird bewusst nicht getippt.
- **Es nimmt auf, aber es erscheint kein Text:** Auf die Statuszeile achten. Nach acht
  Sekunden ohne brauchbaren Ton erscheint dort ein Hinweis:
  - „Kein Ton vom Mikrofon“: Das Mikrofon liefert völlige Stille. Meist ist es
    stummgeschaltet, das falsche Gerät ist gewählt, oder Windows sperrt den Zugriff
    (Einstellungen → Datenschutz und Sicherheit → Mikrofon → Desktop-Apps den Zugriff
    erlauben).
  - „Seit einigen Sekunden nichts zu hören“: Es kommt Ton, aber zu leise, um als Sprache
    zu zählen. Wenn du gerade gar nicht sprichst, ist das normal. Sonst den Pegel erhöhen
    (Windows: Rechtsklick aufs Lautsprechersymbol → Soundeinstellungen → Mikrofon →
    Eingangslautstärke) oder näher ans Mikrofon gehen.
- **Für die Fehlersuche:** Einstellungen → Diagnose → „Log-Ordner öffnen“. Die Datei
  `diktiertool.log` enthält keinen erkannten Text und kann weitergegeben werden.
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
- Mit „Satzzeichen nur per Sprache“ bleibt nach einer Denkpause manchmal ein Wort groß,
  das das Tool noch nicht als klein kennt (z. B. „Mach“, „Danke“, „Egal“). Solche Wörter
  lassen sich in die Liste in `text_postprocess.py` (`_LOWERCASE_WORDS`) aufnehmen, siehe
  [Satzzeichen per Sprache](#satzzeichen-per-sprache).
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
