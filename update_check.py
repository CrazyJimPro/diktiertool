import json
import urllib.error
import urllib.request

REPO = "CrazyJimPro/diktiertool"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


def get_latest_version() -> str | None:
    """Fragt die neueste GitHub-Release-Version ab.

    Lief frueher ueber die GitHub CLI (gh), weil das Repo privat war und ein
    unauthentifizierter Request nur ein 404 geliefert haette. Seit das Repo
    oeffentlich ist, geht das direkt ueber die API - wichtig fuer Windows, wo
    gh so gut wie nie installiert ist und der Update-Hinweis sonst dauerhaft
    ausbliebe. Das Limit von 60 Anfragen pro Stunde und IP reicht dafuer
    reichlich: es wird einmal pro Programmstart gefragt.

    Gibt bei jedem Fehler (kein Netz, Timeout, unerwartete Antwort) None
    zurueck statt zu werfen - der Update-Check ist ein Nice-to-have und darf
    den Programmstart nie verzoegern oder zum Absturz bringen.
    """
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            # GitHub beantwortet Requests ohne User-Agent grundsaetzlich mit 403.
            "User-Agent": "diktiertool-update-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            tag = json.load(response).get("tag_name", "")
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None

    tag = tag.strip()
    return (tag[1:] if tag.startswith("v") else tag) or None


def is_newer(latest: str, current: str) -> bool:
    try:
        return tuple(int(p) for p in latest.split(".")) > tuple(int(p) for p in current.split("."))
    except ValueError:
        return False
