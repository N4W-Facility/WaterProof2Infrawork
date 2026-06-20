"""
cx_Freeze build script — WaterProof2Infrawork standalone (onefolder).

Uso:
    python setup.py build --project-dir <ruta_proyecto>

Si omites --project-dir, usa el directorio de trabajo actual.
Output siempre en: <proyecto>/compiler/WaterProof2Infrawork/

# python setup.py build --project-dir C:/ruta/al/proyecto
"""
import sys
import os
from pathlib import Path

# ── Extraer --project-dir antes de que cx_Freeze consuma sys.argv ──────────
project_dir = None
i = 0
while i < len(sys.argv):
    if sys.argv[i] == "--project-dir" and i + 1 < len(sys.argv):
        project_dir = Path(sys.argv[i + 1]).resolve()
        del sys.argv[i:i + 2]
        break
    if sys.argv[i].startswith("--project-dir="):
        project_dir = Path(sys.argv[i].split("=", 1)[1]).resolve()
        del sys.argv[i]
        break
    i += 1

if project_dir is None:
    project_dir = Path.cwd()

# Agregar proyecto al path para que cx_Freeze resuelva ui/core/config
sys.path.insert(0, str(project_dir))

# ── Resolver directorios de paquetes nativos ────────────────────────────────
from cx_Freeze import setup, Executable
import customtkinter, rasterio, pyproj

CTK_DIR      = Path(customtkinter.__file__).parent
RASTERIO_DIR = Path(rasterio.__file__).parent
PYPROJ_DIR   = Path(pyproj.__file__).parent

output_dir = project_dir / "compiler" / "WaterProof2Infrawork"

# ── Opciones de build ───────────────────────────────────────────────────────
build_exe_options = {
    "packages": [
        "tkinter",
        "customtkinter", "darkdetect",
        "PIL",
        "requests", "bs4", "urllib3", "certifi", "charset_normalizer", "idna",
        "rasterio", "rasterio.warp", "rasterio.crs", "rasterio._features",
        "pyproj", "pyproj.database",
        "numpy",
    ],
    "excludes": [
        "test", "unittest",
        "scipy", "matplotlib", "sklearn",
        "pandas", "geopandas",
        "folium", "branca", "xyzservices",
        "gdal",
    ],
    "include_files": [
        (str(CTK_DIR),                          "lib/customtkinter"),
        (str(RASTERIO_DIR),                     "lib/rasterio"),
        (str(PYPROJ_DIR),                       "lib/pyproj"),
        (str(project_dir / "ui" / "icons"),     "ui/icons/"),
    ],
    "include_msvcr": True,
    "build_exe": str(output_dir),
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="WaterProof2Infrawork",
    version="1.0.0",
    description="WaterProof to Infrawork data pipeline",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            str(project_dir / "app" / "main.py"),
            base=base,
            target_name="WaterProof2Infrawork.exe",
        )
    ],
)
