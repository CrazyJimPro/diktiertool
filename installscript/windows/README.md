# Windows-Installation

Diese Skripte richten das Diktiertool unter Windows ein. Für die normale
Installation braucht man sie nicht einzeln – dafür gibt es die
`DiktiertoolSetup.exe` auf der
[Releases-Seite](https://github.com/CrazyJimPro/diktiertool/releases).

## Was wann läuft

```
DiktiertoolSetup.exe          (Inno Setup, gebaut aus setup.iss)
  └─ bootstrap.ps1            holt den aktuellen Code als ZIP von GitHub
       └─ install.ps1         portables Python + Abhängigkeiten + Verknüpfung
            └─ find-python.ps1   (dot-sourced) findet python-runtime\python.exe
```

| Datei | Aufgabe |
| --- | --- |
| `setup.iss` | Inno-Setup-Skript, erzeugt die `.exe`. Enthält keinen Programmcode, nur die fünf `.ps1` |
| `bootstrap.ps1` | Code von GitHub holen, dann `install.ps1` starten. Pendant zu `../bootstrap.sh` |
| `install.ps1` | Portables Python einrichten, `requirements.txt` installieren, Desktop-Verknüpfung anlegen. Pendant zu `../../setup.sh` |
| `find-python.ps1` | Gemeinsame Python-Auflösung, per Dot-Source eingebunden |
| `start.ps1` | Startet `main.py`. Pendant zu `../../start.sh` |
| `uninstall.ps1` | Laufendes Programm beenden, Verknüpfung entfernen |

## Warum portables Python statt des vorhandenen?

`install.ps1` nutzt **nie** ein Python aus dem `PATH`, sondern lädt immer das
offizielle „embeddable package" von python.org nach `python-runtime\`. Grund:
`pip` installiert in die globalen `site-packages` des jeweiligen Interpreters.
Ein vorhandenes System-Python hätte sich rund 30 Pakete eingefangen, die es nie
angefordert hat – und die Deinstallation könnte sie nicht zuverlässig wieder
entfernen, weil nicht feststellbar ist, welche davon schon vorher gebraucht
wurden. So bleibt alles in einem Ordner, den die Deinstallation einfach löscht.

Eine Eigenheit dieses Pakets: seine `._pth`-Datei legt `sys.path` abschließend
fest und schaltet dabei die übliche Regel ab, dass der Ordner des gestarteten
Skripts im Suchpfad landet. `install.ps1` ergänzt deshalb `import site`,
`Lib\site-packages` und `..` – ohne das startet `main.py` mit
`No module named 'gui'`.

## Selbst bauen

```
iscc installscript\windows\setup.iss
```

Ergebnis: `installscript\windows\dist\DiktiertoolSetup.exe`. Normalerweise
übernimmt das der Workflow `.github/workflows/build-windows-installer.yml` –
bei einem `v*`-Tag hängt er die `.exe` direkt ans Release, per
„Run workflow" baut er sie nur zum Herunterladen.

## Von Hand einrichten (ohne .exe)

Etwa auf einem Entwicklungsrechner, auf dem das Repo schon per `git` liegt:

```powershell
powershell -ExecutionPolicy Bypass -File installscript\windows\install.ps1 -InstallDir "<Pfad zum Repo>"
```

`bootstrap.ps1` erkennt eine Git-Arbeitskopie übrigens an ihrem `.git`-Ordner
und überschreibt sie dann *nicht* mit dem ZIP-Stand.

## Fehlersuche

Jede Einrichtung protokolliert nach `install.log` im Installationsordner
(`%LOCALAPPDATA%\Diktiertool\install.log`) – der `[Run]`-Schritt von Inno Setup
zeigt bei einem Fehler sonst nur „fertig" ohne jeden Hinweis.

Startet das Tool nicht, hilft der Startmenü-Eintrag **„Diktiertool starten (mit
Meldungen)"**: derselbe Start, aber mit sichtbarer Konsole.

Der Installationspfad darf höchstens 100 Zeichen lang sein. Windows erlaubt pro
Datei nur 260 Zeichen, und `onnxruntime` legt unterhalb des Ordners Pfade von
rund 135 Zeichen an – sonst bricht `pip` mitten im Entpacken mit einem
nichtssagenden `[Errno 2] No such file or directory` ab. `setup.iss` und
`install.ps1` prüfen das beide vorher.
