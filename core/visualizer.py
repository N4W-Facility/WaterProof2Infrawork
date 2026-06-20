"""
Generación de imágenes RGBA a partir de rasters de profundidad y velocidad.

Procesamiento ventana por ventana — compatible con rasters >1GB.
Rangos globales calculados antes de generar para garantizar comparabilidad.
"""
import re
from pathlib import Path

import numpy as np
import rasterio


# ── Defaults ───────────────────────────────────────────────────────────────────

# 5 anclas: (posición normalizada 0-1, hex)
DEFAULT_ANCHOR_COLORS = [
    "#BFD9FF",   # 0.00 — muy superficial
    "#4B9FE8",   # 0.25 — tobillo
    "#0066CC",   # 0.50 — cintura
    "#004D99",   # 0.75 — pecho
    "#03045E",   # 1.00 — extremo
]
DEFAULT_DANGER_COLOR  = "#03045E"   # Azul más oscuro
DEFAULT_VEL_INTENSITY = 0.55        # 0 = sin tinte, 1 = máximo
DEFAULT_VEL_THRESHOLD = 0.5         # m/s — por debajo de este valor no se aplica tinte
DEFAULT_DRY_THRESH    = 0.05        # metros — por debajo = seco/transparente
_ALPHA_WET            = 220         # alpha de píxeles con agua
_ANCHOR_STOPS         = np.array([0.0, 0.25, 0.50, 0.75, 1.0], dtype=np.float32)


# ── Utilidades de color ────────────────────────────────────────────────────────

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _build_cmap(anchor_hexes: list[str]) -> np.ndarray:
    """Construye matriz (5, 3) float32 con los colores RGB de las anclas."""
    return np.array([hex_to_rgb(h) for h in anchor_hexes], dtype=np.float32)


def _apply_colormap(d_norm: np.ndarray, cmap: np.ndarray) -> np.ndarray:
    """
    Interpola d_norm [0,1] sobre el colormap de 5 anclas.
    Retorna (H, W, 3) float32.
    """
    stops  = _ANCHOR_STOPS
    idx    = np.searchsorted(stops, d_norm, side="right") - 1
    idx    = np.clip(idx, 0, len(stops) - 2)

    lo     = stops[idx]
    hi     = stops[idx + 1]
    denom  = np.where((hi - lo) == 0, 1.0, hi - lo)
    t      = np.clip((d_norm - lo) / denom, 0, 1)[..., np.newaxis]

    c_lo   = cmap[idx]
    c_hi   = cmap[idx + 1]
    return (c_lo + t * (c_hi - c_lo)).astype(np.float32)


# ── Emparejamiento de archivos ─────────────────────────────────────────────────

def _pair_key(filename: str) -> str:
    return re.sub(r"^(Flood|Velocity)_", "", Path(filename).stem)


def _find_pairs(processed_dir: Path) -> list[tuple[Path, Path]]:
    flood_dir = processed_dir / "Flood"
    vel_dir   = processed_dir / "Velocity"
    flood_map = {_pair_key(f.name): f for f in sorted(flood_dir.glob("Flood_*.tif"))}
    vel_map   = {_pair_key(f.name): f for f in sorted(vel_dir.glob("Velocity_*.tif"))}
    keys      = sorted(set(flood_map) & set(vel_map))
    return [(flood_map[k], vel_map[k]) for k in keys]


# ── API pública ────────────────────────────────────────────────────────────────

def scan_global_stats(processed_dir: Path, progress_cb=None, dry_thresh: float = DEFAULT_DRY_THRESH) -> dict:
    """
    Calcula min/max globales de profundidad y velocidad leyendo ventana por ventana.

    Parámetros
    ----------
    processed_dir : carpeta con subcarpetas Flood/ y Velocity/.
    progress_cb   : callable(current, total).
    dry_thresh    : umbral mínimo de profundidad para considerar agua.

    Retorna
    -------
    dict: depth_min, depth_max, vel_min, vel_max.
    """
    pairs = _find_pairs(processed_dir)
    if not pairs:
        raise FileNotFoundError(f"No se encontraron pares Flood/Velocity en {processed_dir}")

    d_min = np.inf;  d_max = -np.inf
    v_min = np.inf;  v_max = -np.inf
    total = len(pairs)

    for i, (flood_path, vel_path) in enumerate(pairs, 1):
        with rasterio.open(flood_path) as fd, rasterio.open(vel_path) as fv:
            nd_d, nd_v = fd.nodata, fv.nodata
            for _, win in fd.block_windows(1):
                d = fd.read(1, window=win).astype(np.float32)
                v = fv.read(1, window=win).astype(np.float32)
                mask = np.isfinite(d) & np.isfinite(v) & (d > dry_thresh)
                if nd_d is not None: mask &= (d != nd_d)
                if nd_v is not None: mask &= (v != nd_v)
                if mask.any():
                    d_min = min(d_min, float(d[mask].min()))
                    d_max = max(d_max, float(d[mask].max()))
                    v_min = min(v_min, float(v[mask].min()))
                    v_max = max(v_max, float(v[mask].max()))
        if progress_cb:
            progress_cb(i, total)

    return {
        "depth_min": max(0.0, d_min),
        "depth_max": d_max,
        "vel_min":   max(0.0, v_min),
        "vel_max":   v_max,
    }


def generate_rgba(
    flood_path: Path,
    vel_path: Path,
    out_path: Path,
    stats: dict,
    anchor_colors: list[str]  = DEFAULT_ANCHOR_COLORS,
    danger_color: str         = DEFAULT_DANGER_COLOR,
    vel_intensity: float      = DEFAULT_VEL_INTENSITY,
    vel_threshold: float      = DEFAULT_VEL_THRESHOLD,
    dry_thresh: float         = DEFAULT_DRY_THRESH,
    progress_cb               = None,
) -> None:
    """
    Genera un GeoTIFF RGBA a partir de un par Flood + Velocity.

    Parámetros
    ----------
    flood_path    : raster de profundidad (m).
    vel_path      : raster de velocidad (m/s).
    out_path      : ruta de salida.
    stats         : dict depth_min/max, vel_min/max (de scan_global_stats).
    anchor_colors : lista de 5 hex — gradiente de profundidad.
    danger_color  : hex del tinte de velocidad alta.
    vel_intensity : 0–1, qué tan fuerte es el tinte de velocidad.
    vel_threshold : m/s — velocidad mínima a partir de la cual se aplica el tinte.
    dry_thresh    : m — por debajo de este valor el pixel es transparente.
    progress_cb   : callable(current, total_windows).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmap   = _build_cmap(anchor_colors)
    danger = np.array(hex_to_rgb(danger_color), dtype=np.float32)

    d_range = max(stats["depth_max"] - stats["depth_min"], 1e-6)
    v_range = max(stats["vel_max"]   - stats["vel_min"],   1e-6)

    with rasterio.open(flood_path) as fd, rasterio.open(vel_path) as fv:
        nd_d, nd_v = fd.nodata, fv.nodata
        profile = fd.profile.copy()
        profile.update(count=4, dtype="uint8", compress="lzw", nodata=None)
        windows = list(fd.block_windows(1))

        with rasterio.open(out_path, "w", **profile) as dst:
            for i, (_, win) in enumerate(windows, 1):
                d = fd.read(1, window=win).astype(np.float32)
                v = fv.read(1, window=win).astype(np.float32)

                wet = np.isfinite(d) & np.isfinite(v) & (d > dry_thresh)
                if nd_d is not None: wet &= (d != nd_d)
                if nd_v is not None: wet &= (v != nd_v)

                d_norm = np.clip((d - stats["depth_min"]) / d_range, 0, 1)
                v_above = np.maximum(v - vel_threshold, 0.0)
                v_range_above = max(stats["vel_max"] - vel_threshold, 1e-6)
                v_norm = np.clip(v_above / v_range_above, 0, 1)

                rgb  = _apply_colormap(d_norm, cmap)
                v3   = v_norm[..., np.newaxis]
                rgb  = rgb * (1 - v3 * vel_intensity) + danger * (v3 * vel_intensity)
                rgb  = np.clip(rgb, 0, 255)

                rgba = np.zeros((*d.shape, 4), dtype=np.uint8)
                rgba[wet, :3] = rgb[wet].astype(np.uint8)
                rgba[:, :, 3] = np.where(wet, _ALPHA_WET, 0).astype(np.uint8)

                for band in range(4):
                    dst.write(rgba[:, :, band], band + 1, window=win)

                if progress_cb:
                    progress_cb(i, len(windows))


def generate_all(
    processed_dir: Path,
    stats: dict,
    anchor_colors: list[str]  = DEFAULT_ANCHOR_COLORS,
    danger_color: str         = DEFAULT_DANGER_COLOR,
    vel_intensity: float      = DEFAULT_VEL_INTENSITY,
    vel_threshold: float      = DEFAULT_VEL_THRESHOLD,
    dry_thresh: float         = DEFAULT_DRY_THRESH,
    progress_cb               = None,
) -> list[Path]:
    """
    Genera imágenes RGBA para todos los pares Flood/Velocity.

    Parámetros
    ----------
    processed_dir : carpeta con Flood/ y Velocity/ reproyectados.
    stats         : resultado de scan_global_stats.
    anchor_colors : 5 hex del gradiente de profundidad.
    danger_color  : hex del tinte de velocidad.
    vel_intensity : 0–1, intensidad del tinte.
    vel_threshold : m/s — velocidad mínima para aplicar el tinte.
    dry_thresh    : umbral mínimo de profundidad.
    progress_cb   : callable(current, total).

    Retorna
    -------
    Lista de rutas generadas.
    """
    pairs   = _find_pairs(processed_dir)
    out_dir = processed_dir.parent / "visualize"
    results = []

    for i, (flood_path, vel_path) in enumerate(pairs, 1):
        key      = _pair_key(flood_path.name)
        out_path = out_dir / f"RGBA_{key}.tif"
        generate_rgba(
            flood_path, vel_path, out_path, stats,
            anchor_colors, danger_color, vel_intensity, vel_threshold, dry_thresh,
        )
        results.append(out_path)
        if progress_cb:
            progress_cb(i, len(pairs))

    return results


# python -m core.visualizer <processed_dir>
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python -m core.visualizer <processed_dir>")
        sys.exit(1)

    processed = Path(sys.argv[1])
    print("Escaneando rangos...")
    stats = scan_global_stats(processed, lambda c, t: print(f"  {c}/{t}", end="\r"))
    print(f"\nDepth:    {stats['depth_min']:.2f} – {stats['depth_max']:.2f} m")
    print(f"Velocity: {stats['vel_min']:.2f} – {stats['vel_max']:.2f} m/s")
    print("\nGenerando RGBA...")
    files = generate_all(processed, stats, progress_cb=lambda c, t: print(f"  {c}/{t}", end="\r"))
    print(f"\nDone. {len(files)} archivos.")
