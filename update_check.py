import subprocess

REPO = "CrazyJimPro/diktiertool"


def get_latest_version() -> str | None:
    """Fragt die neueste GitHub-Release-Version ab. Laeuft ueber gh (nicht die rohe
    GitHub-API), weil das Repo privat ist - ein unauthentifizierter Request wuerde nur
    ein 404 liefern. Gibt bei jedem Fehler (gh fehlt, nicht angemeldet, kein Netz,
    Timeout) None zurueck statt zu werfen - der Update-Check ist ein Nice-to-have und
    darf den Programmstart nie verzoegern oder zum Absturz bringen."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/releases/latest", "--jq", ".tag_name"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    tag = result.stdout.strip()
    return (tag[1:] if tag.startswith("v") else tag) or None


def is_newer(latest: str, current: str) -> bool:
    try:
        return tuple(int(p) for p in latest.split(".")) > tuple(int(p) for p in current.split("."))
    except ValueError:
        return False
