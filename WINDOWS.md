# Diktiertool unter Windows

Anleitung für die Installation, Benutzung, Updates und Deinstallation unter Windows. Was
auf Windows und Linux gleich ist (Knöpfe, Audiodateien transkribieren, Diktieren per Taste,
Einstellungen, Fehlersuche …), steht in der [allgemeinen Anleitung](README.md). Die
Linux-Anleitung gibt es unter [LINUX.md](LINUX.md).

- [Installation](#installation)
- [Benutzung](#benutzung)
- [Wo landet der Text?](#wo-landet-der-text)
- [Update](#update)
- [Deinstallation](#deinstallation)
- [Bekannte Eigenheiten unter Windows](#bekannte-eigenheiten-unter-windows)

---

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
[Einstellungen](README.md#einstellungen) ein.

## Update

Beim Start prüft das Tool im Hintergrund, ob ein neueres Release existiert. Ist eines
verfügbar, erscheint neben der Versionsnummer im Header ein Hinweis-Badge – ein Klick
darauf öffnet die Release-Seite. Dort die neue `DiktiertoolSetup.exe` herunterladen und
ausführen; sie aktualisiert die vorhandene Installation, ohne Python oder das
Spracherkennungsmodell erneut zu laden.

## Deinstallation

Über "Apps & Features" (oder den Eintrag "Deinstallieren" im Startmenü). Entfernt den
kompletten Programmordner samt portablem Python und Modell-Zwischenspeicher, außerdem die
Einstellungen unter `%APPDATA%\Diktiertool` und das Diagnose-Log unter
`%LOCALAPPDATA%\Diktiertool\logs`.
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
