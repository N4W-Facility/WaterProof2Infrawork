"""
Transformaciones espaciales: búsqueda de CRS y reproyección de rasters.
"""
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj.database import query_crs_info
from pyproj import CRS


def search_crs(query: str) -> list[dict]:
    """
    Busca sistemas de coordenadas por nombre o código.

    Parámetros
    ----------
    query : str
        Texto de búsqueda (ej: 'Colombia', 'MAGNA', 'UTM zone 18').

    Retorna
    -------
    Lista de dicts con claves: auth_name, code, name, crs_str.
    Máximo 20 resultados.
    """
    terms = [t.lower() for t in query.split()]
    results = []
    for info in query_crs_info():
        target = f"{info.name} {info.code}".lower()
        if all(t in target for t in terms):
            results.append({
                "auth_name": info.auth_name,
                "code":      info.code,
                "name":      info.name,
                "crs_str":   f"{info.auth_name}:{info.code}",
            })
        if len(results) >= 20:
            break
    return results


def reproject_raster(src: Path, dst: Path, target_crs: str) -> None:
    """
    Reproyecta un raster al CRS indicado.

    Parámetros
    ----------
    src        : ruta al archivo de entrada.
    dst        : ruta al archivo de salida (se crea si no existe).
    target_crs : CRS destino en cualquier formato válido de pyproj
                 (ej: 'EPSG:3116', 'EPSG:4326').
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    crs_out = CRS.from_user_input(target_crs)

    with rasterio.open(src) as src_ds:
        transform, width, height = calculate_default_transform(
            src_ds.crs, crs_out,
            src_ds.width, src_ds.height,
            *src_ds.bounds,
        )
        profile = src_ds.profile.copy()
        profile.update(
            crs=crs_out,
            transform=transform,
            width=width,
            height=height,
            compress="lzw",
        )

        with rasterio.open(dst, "w", **profile) as dst_ds:
            for band in range(1, src_ds.count + 1):
                reproject(
                    source=rasterio.band(src_ds, band),
                    destination=rasterio.band(dst_ds, band),
                    src_transform=src_ds.transform,
                    src_crs=src_ds.crs,
                    dst_transform=transform,
                    dst_crs=crs_out,
                    resampling=Resampling.nearest,
                )


def reproject_case(
    project_dir: Path,
    target_crs: str,
    progress_cb=None,
) -> list[Path]:
    """
    Reproyecta todos los rasters del proyecto al CRS indicado.

    Parámetros
    ----------
    project_dir  : carpeta raíz del proyecto (contiene Flood/, Velocity/, Raster/).
    target_crs   : CRS destino (ej: 'EPSG:3116').
    progress_cb  : callable(current, total) para reportar progreso (opcional).

    Retorna
    -------
    Lista de rutas de archivos reproyectados (en project_dir/processed/).
    """
    sources: list[tuple[Path, Path]] = []

    for folder in ["Flood", "Velocity"]:
        src_dir = project_dir / folder
        if src_dir.exists():
            for tif in sorted(src_dir.glob("*.tif")):
                dst = project_dir / "processed" / folder / tif.name
                sources.append((tif, dst))

    raster_dir = project_dir / "Raster"
    for name in ("DEM.tif", "activity_portfolio_total.tif"):
        src = raster_dir / name
        if src.exists():
            sources.append((src, project_dir / "processed" / "Raster" / name))

    for bau in raster_dir.glob("*_BAU.tif"):
        sources.append((bau, project_dir / "processed" / "Raster" / bau.name))

    total = len(sources)
    done = []
    for i, (src, dst) in enumerate(sources, 1):
        reproject_raster(src, dst, target_crs)
        done.append(dst)
        if progress_cb:
            progress_cb(i, total)

    return done


# python -m core.transformer 1011_7_2025-12-23 EPSG:3116 /path/to/project
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Uso: python -m core.transformer <case_folder> <crs> <project_dir>")
        sys.exit(1)

    case_folder, crs, project_dir = sys.argv[1], sys.argv[2], sys.argv[3]

    def progress(current, total):
        print(f"  {current}/{total}", end="\r")

    result = reproject_case(Path(project_dir), case_folder, crs, progress)
    print(f"\nDone. {len(result)} files saved.")
