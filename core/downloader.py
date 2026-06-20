"""
Descarga de datos espaciales desde WaterProof.

Dado un ID de caso de estudio, localiza la carpeta correspondiente en el
servidor, descubre la subcarpeta WI_* y descarga los archivos de Flood,
Velocity y DEM.tif.
"""
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://water-proof.org/outputs/fastflood"


def _list_links(url: str, session: requests.Session) -> list[str]:
    """Retorna los hrefs del directory listing HTML de una URL."""
    response = session.get(url + "/", timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return [a["href"] for a in soup.find_all("a", href=True)]


def check_case_exists(case_id: int) -> bool:
    """Verifica si un ID de caso existe en WaterProof sin descargar nada."""
    try:
        _find_case_folder(case_id, requests.Session())
        return True
    except (ValueError, requests.RequestException):
        return False


def _find_case_folder(case_id: int, session: requests.Session) -> str:
    """
    Busca en el listado raíz la carpeta que corresponde al ID de caso.

    Retorna el nombre completo de la carpeta (ej: '1011_89_2026-3-13').
    Lanza ValueError si no se encuentra.
    """
    links = _list_links(BASE_URL, session)
    pattern = re.compile(rf"^\d+_{case_id}_\d{{4}}-\d+-\d+/?$")
    for link in links:
        if pattern.match(link):
            return link.rstrip("/")
    raise ValueError(f"No se encontró carpeta para el caso ID={case_id}")


def _find_wi_folder(case_folder: str, session: requests.Session) -> str:
    """
    Descubre el nombre de la subcarpeta WI_* dentro del caso de estudio.

    Retorna el nombre de la carpeta (ej: 'WI_5').
    Lanza ValueError si no se encuentra.
    """
    url = f"{BASE_URL}/{case_folder}"
    links = _list_links(url, session)
    for link in links:
        if re.match(r"^WI_\d+/?$", link):
            return link.rstrip("/")
    raise ValueError(f"No se encontró carpeta WI_* en {url}")


def _download_file(url: str, dest: Path, session: requests.Session) -> None:
    """Descarga un archivo desde url y lo guarda en dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


def _find_bau_file(base: str, session: requests.Session) -> str:
    """
    Descubre el nombre del archivo *_BAU.tif en in/02-INVEST/CARBON/.

    Retorna el nombre del archivo (ej: 'scenario_BAU.tif').
    Lanza ValueError si no se encuentra.
    """
    url = f"{base}/in/02-INVEST/CARBON"
    links = _list_links(url, session)
    for link in links:
        if link.lower().endswith("_bau.tif"):
            return link
    raise ValueError(f"No se encontró archivo *_BAU.tif en {url}")


def _download_folder(url: str, dest: Path, session: requests.Session, file_cb=None) -> list[Path]:
    """
    Lista y descarga todos los archivos de un directory listing remoto.

    Retorna la lista de rutas locales descargadas.
    """
    links = _list_links(url, session)
    downloaded = []
    for link in links:
        if link.startswith("?") or link in ("..", "/", "./") or link.endswith("/"):
            continue
        file_url = f"{url}/{link}"
        local_path = dest / link
        print(f"  Descargando: {link}")
        _download_file(file_url, local_path, session)
        downloaded.append(local_path)
        if file_cb:
            file_cb()
    return downloaded


def download_case(case_id: int, output_dir: Path, progress_cb=None) -> dict:
    """
    Descarga los archivos de un caso de estudio WaterProof.

    Parámetros
    ----------
    case_id : int
        ID del caso de estudio (ej: 1011).
    output_dir : Path
        Carpeta local donde guardar los archivos descargados.

    Retorna
    -------
    dict con claves 'flood', 'velocity', 'dem' y las rutas descargadas.
    """
    session = requests.Session()

    print(f"[1/4] Buscando carpeta para caso ID={case_id}...")
    case_folder = _find_case_folder(case_id, session)
    print(f"      Encontrada: {case_folder}")

    print(f"[2/4] Buscando subcarpeta WI_*...")
    wi_folder = _find_wi_folder(case_folder, session)
    print(f"      Encontrada: {wi_folder}")

    base = f"{BASE_URL}/{case_folder}/{wi_folder}"

    TOTAL = 63  # 30 Flood + 30 Velocity + 1 DEM + 1 portfolio + 1 BAU
    done  = [0]

    def _tick():
        done[0] += 1
        if progress_cb:
            progress_cb(done[0], TOTAL)

    print(f"[3/4] Descargando Flood y Velocity...")
    flood_files = _download_folder(
        f"{base}/out/06-FLOOD/Flood",
        output_dir / "Flood",
        session,
        file_cb=_tick,
    )
    velocity_files = _download_folder(
        f"{base}/out/06-FLOOD/Velocity",
        output_dir / "Velocity",
        session,
        file_cb=_tick,
    )

    print(f"[4/6] Descargando DEM.tif...")
    dem_path = output_dir / "Raster" / "DEM.tif"
    _download_file(f"{base}/in/06-FLOOD/Raster/DEM.tif", dem_path, session)
    _tick()

    print(f"[5/6] Descargando activity_portfolio_total.tif...")
    portfolio_path = output_dir / "Raster" / "activity_portfolio_total.tif"
    _download_file(
        f"{base}/out/03-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/activity_portfolio_total.tif",
        portfolio_path,
        session,
    )
    _tick()

    print(f"[6/6] Descargando archivo BAU...")
    bau_name = _find_bau_file(base, session)
    bau_path = output_dir / "Raster" / bau_name
    _download_file(f"{base}/in/02-INVEST/CARBON/{bau_name}", bau_path, session)
    _tick()

    print("Descarga completada.")
    return {
        "case_folder": case_folder,
        "wi_folder":   wi_folder,
        "flood":       flood_files,
        "velocity":    velocity_files,
        "dem":         dem_path,
        "portfolio":   portfolio_path,
        "bau":         bau_path,
    }


# python -m core.downloader 1011 data/raw
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python -m core.downloader <case_id> <output_dir>")
        sys.exit(1)

    result = download_case(int(sys.argv[1]), Path(sys.argv[2]))
    print(f"\nResumen:")
    print(f"  Flood:    {len(result['flood'])} archivos")
    print(f"  Velocity: {len(result['velocity'])} archivos")
    print(f"  DEM:      {result['dem']}")
