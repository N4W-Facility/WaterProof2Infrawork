# WaterProof → InfraWorks Converter

Desktop tool that automates the full pipeline from WaterProof spatial data to InfraWorks-ready RGBA rasters.

---

## What it does

**Start** — welcome screen shown on launch. Describes the three steps and navigates to Download.

**Download** — downloads all raw flood simulation rasters from the WaterProof server by entering a Case ID. Discovers folder structure automatically. 63 files total.

**Transform** — reprojects every downloaded raster to the coordinate system used by the InfraWorks project. Search CRS by name (same name shown in InfraWorks Project Settings) and select from a live list.

**Visualize** — generates color-mapped RGBA GeoTIFFs from the Flood + Velocity pairs. A global scan step ensures all 30 images share the same color scale. Colors, depth/velocity ranges, and tint intensity are editable before generating.

---

## Files downloaded per case

| Folder | File | Source path on WaterProof server |
|--------|------|----------------------------------|
| `Flood/` | 30 depth rasters | `out/06-FLOOD/Flood/` |
| `Velocity/` | 30 velocity rasters | `out/06-FLOOD/Velocity/` |
| `Raster/` | `DEM.tif` | `in/06-FLOOD/Raster/DEM.tif` |
| `Raster/` | `activity_portfolio_total.tif` | `out/03-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/activity_portfolio_total.tif` |
| `Raster/` | `*_BAU.tif` (name discovered at runtime) | `in/02-INVEST/CARBON/` |

The `WI_*` subfolder inside each case folder is discovered automatically at runtime.

---

## Project folder structure (user data)

```
<project_dir>/
├── Flood/              # 30 flood-depth rasters (downloaded)
├── Velocity/           # 30 velocity rasters (downloaded)
├── Raster/             # DEM.tif · activity_portfolio_total.tif · *_BAU.tif
├── processed/
│   ├── Flood/          # reprojected flood rasters
│   ├── Velocity/       # reprojected velocity rasters
│   └── Raster/         # reprojected DEM, portfolio and BAU
└── visualize/          # RGBA_<scenario>_<TR>.tif (30 files)
```

---

## Repository structure

```
06-Autodesk/
├── app/
│   └── main.py                  # entry point — launch this file
├── setup.py                     # cx_Freeze build configuration
├── installer.iss                # Inno Setup installer script
├── build.bat                    # Step 1: compile with cx_Freeze
├── build_installer.bat          # Step 2: package with Inno Setup
├── environment.yml              # conda environment definition
├── requirements.txt             # pip freeze snapshot (reference only)
├── config/
│   ├── settings.py              # APP_DIR, PREFS_FILE, WATERPROOF_URL
│   ├── prefs.py                 # read/write prefs.json (project_dir, last_crs)
│   └── credentials.env         # placeholder — WaterProof needs no auth currently
├── core/
│   ├── downloader.py            # HTML scraping + file download (63 files)
│   ├── transformer.py           # CRS search + rasterio reprojection
│   ├── visualizer.py            # RGBA generation (windowed, depth + velocity)
│   └── exporter.py             # placeholder for future InfraWorks export
├── ui/
│   ├── app.py                   # main window, tab bar, logo display
│   ├── theme.py                 # COLORS, FONT constants
│   ├── icons/                   # Logo_WP.png · Logo_TNC.png · Icon_WP_Autodesk.png
│   ├── components/
│   │   ├── section_label.py
│   │   └── color_swatch.py      # color picker button + hex field
│   └── views/
│       ├── start_view.py
│       ├── download_view.py
│       ├── transform_view.py
│       ├── visualize_view.py
│       └── export_view.py       # placeholder
├── compiler/                    # build output (generated, not committed)
│   ├── WaterProof2Infrawork/    # cx_Freeze output folder (Step 1)
│   └── WaterProof2Infrawork_v*.exe  # Inno Setup installer (Step 2)
└── tests/                       # placeholders (not yet implemented)
```

---

## Environment setup

Requires [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda on Windows.

```bash
# Create the environment
conda env create -f environment.yml

# Activate
conda activate wp_autodesk

# Install cx_Freeze (not in environment.yml — install once manually)
pip install cx_Freeze
```

Key packages:
- `python 3.12`
- `rasterio 1.5` + `pyproj 3.7` + `gdal 3.12` — geospatial stack
- `customtkinter 5.2.2` — UI framework
- `pillow 12` — image loading
- `requests` + `beautifulsoup4` — WaterProof server scraping
- `scipy` — interpolation for RGBA gradient
- `cx_Freeze` — standalone executable compilation

---

## Running in development

```bash
conda activate wp_autodesk
python app/main.py
```

Running individual core modules directly (each has a `__main__` block):

```bash
# Test download for case 89
python -m core.downloader 89 data/raw

# Test reprojection
python -m core.transformer <case_folder> EPSG:3116 /path/to/project
```

---

## Building the executable

The build is a two-step process: **cx_Freeze** compiles the app into a folder, then **Inno Setup** packages that folder into a single installer `.exe`.

### Prerequisites

- conda environment `wp_autodesk` active with `cx_Freeze` installed (see Environment setup)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) installed at `C:\Program Files (x86)\Inno Setup 6\`
- Run all commands from a **Windows** terminal (CMD or PowerShell), not WSL

---

### Step 1 — Compile with cx_Freeze

```bat
build.bat
```

Or with an explicit project path:

```bat
build.bat C:\path\to\06-Autodesk
```

What it does:
- Activates `wp_autodesk` conda environment
- Runs `python setup.py build --project-dir <path>`
- Copies all Python packages, DLLs, and UI assets into `compiler\WaterProof2Infrawork\`

Output:

```
compiler\
└── WaterProof2Infrawork\
    ├── WaterProof2Infrawork.exe
    ├── python312.dll
    ├── *.dll
    ├── lib\
    │   ├── customtkinter\
    │   ├── rasterio\
    │   ├── pyproj\
    │   └── ...
    └── ui\
        └── icons\
```

Verify the build works before proceeding to Step 2:

```bat
compiler\WaterProof2Infrawork\WaterProof2Infrawork.exe
```

---

### Step 2 — Create the installer with Inno Setup

```bat
build_installer.bat
```

What it does:
- Waits 10 seconds (buffer after Step 1 if run in sequence)
- Calls `ISCC.exe installer.iss`
- Reads everything from `compiler\WaterProof2Infrawork\` and packages it

Output:

```
compiler\
└── WaterProof2Infrawork_v1.0.0.exe   ← distributable installer
```

Or compile the installer manually from the Inno Setup GUI:
1. Open `installer.iss` in Inno Setup Compiler
2. Press **Compile** (F9)

---

### What the installer does

- Installs to `%LOCALAPPDATA%\WaterProof2Infrawork\` (no admin required)
- Creates Start Menu shortcuts
- Optionally creates a desktop shortcut
- Creates an initial empty `prefs.json` on first install
- Registers an uninstaller
- On upgrade: wipes `lib\` before copying new files to avoid stale dependencies

---

### Silent install

```bat
WaterProof2Infrawork_v1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

---

### Common build errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: cx_Freeze` | Not installed | `pip install cx_Freeze` |
| App launches but icons missing | `ui/icons/` not found | Verify `include_files` in `setup.py` includes the icons path |
| `PROJ not initialized` at runtime | `PROJ_DATA` env var not set | `settings.py` must set env vars from `sys.executable` path before importing rasterio |
| Installer fails — Access Denied | Trying to install to Program Files | `PrivilegesRequired=lowest` in `installer.iss` + install dir set to `{localappdata}` |
| Installer script encoding error | Unix line endings (LF) in `.iss` | Save `installer.iss` with CRLF (VS Code: click LF in status bar → select CRLF) |
| Old files persist after upgrade | Missing `[InstallDelete]` section | `installer.iss` already includes `Type: filesandordirs; Name: "{app}\lib"` |

---

## Configuration persistence

User preferences are saved to `prefs.json` next to the executable (or next to `app/main.py` in dev mode):

```json
{
  "project_dir": "C:/Users/.../my_project",
  "last_crs": "EPSG:3116"
}
```

`config/prefs.py` handles reading and writing. `config/settings.py` detects whether the app is running frozen (compiled) or as a script:

```python
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent  # next to the .exe
else:
    APP_DIR = Path(__file__).resolve().parent.parent  # project root
```

---

## Color scheme (Visualize tab)

| Element | Default |
|---------|---------|
| Depth gradient (5 anchors) | Pale blue → deep navy |
| Danger tint (high velocity) | Orange-red |
| Tint intensity | 0.6 |
| Min depth threshold | from scan |
| Max depth scale | from scan |
| Max velocity scale | from scan |

All parameters are editable in the UI before generating. The **Scan** step must run first to pre-fill the min/max values.

---

## Known limitations / future work

- **Export tab**: `core/exporter.py` and `ui/views/export_view.py` are empty placeholders. The exact format required by InfraWorks is pending definition.
- **Tests**: `tests/` contains placeholders. Priority targets are `downloader.py` (server structure changes) and `transformer.py` (CRS edge cases).
- **WaterProof auth**: `config/credentials.env` is prepared but unused — the server currently requires no authentication.
