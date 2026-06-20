"""
Parámetros generales de la aplicación.

La ruta del proyecto la define el usuario en runtime; no hay rutas
de datos hardcodeadas aquí. Compatible con compilación (PyInstaller).
"""
import sys
from pathlib import Path

# Directorio del ejecutable (funciona tanto en desarrollo como compilado)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

# Archivo donde se persiste la última ruta de proyecto usada
PREFS_FILE = APP_DIR / "prefs.json"

WATERPROOF_URL = "https://water-proof.org"
DEFAULT_CRS    = "EPSG:4326"
