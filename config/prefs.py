"""
Persistencia de preferencias de usuario (ruta del proyecto, etc.).

Guarda y carga un JSON junto al ejecutable. Compatible con PyInstaller.
"""
import json
from pathlib import Path

from config.settings import PREFS_FILE


def load() -> dict:
    """Carga las preferencias desde disco. Retorna {} si no existen."""
    if PREFS_FILE.exists():
        return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    return {}


def save(prefs: dict) -> None:
    """Guarda el diccionario de preferencias en disco."""
    PREFS_FILE.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def get_project_dir() -> Path | None:
    """Retorna la última ruta de proyecto usada, o None si no hay ninguna."""
    p = load().get("project_dir")
    return Path(p) if p else None


def set_project_dir(path: Path) -> None:
    """Persiste la ruta del proyecto elegida por el usuario."""
    prefs = load()
    prefs["project_dir"] = str(path)
    save(prefs)


def get_last_crs() -> str | None:
    """Retorna el último CRS usado (ej: 'EPSG:3116'), o None si no hay ninguno."""
    return load().get("last_crs")


def set_last_crs(crs: str) -> None:
    """Persiste el último CRS seleccionado por el usuario."""
    prefs = load()
    prefs["last_crs"] = crs
    save(prefs)
