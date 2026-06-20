import sys
import os

if getattr(sys, "frozen", False):
    _base = os.path.dirname(sys.executable)
    os.environ["PROJ_DATA"]    = os.path.join(_base, "lib", "pyproj", "proj_dir", "share", "proj")
    os.environ["GDAL_DATA"]    = os.path.join(_base, "lib", "rasterio", "gdal_data")
    os.environ["PROJ_NETWORK"] = "OFF"
    # customtkinter: forzar carga desde lib/ empaquetado
    _ctk_parent = os.path.join(_base, "lib")
    if _ctk_parent not in sys.path:
        sys.path.insert(0, _ctk_parent)

from ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()

