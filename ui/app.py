"""
Ventana principal de la aplicación.
"""
import customtkinter as ctk
from PIL import Image

import config.prefs as prefs
from config.settings import APP_DIR
from ui.theme import COLORS, FONT
from ui.views.start_view import StartView
from ui.views.download_view import DownloadView
from ui.views.transform_view import TransformView
from ui.views.visualize_view import VisualizeView


def _has_downloaded_files() -> bool:
    """Verifica si el proyecto activo tiene archivos descargados."""
    project_dir = prefs.get_project_dir()
    if not project_dir:
        return False
    flood_dir = project_dir / "Flood"
    return flood_dir.exists() and any(flood_dir.glob("*.tif"))


def _has_reprojected_files() -> bool:
    """Verifica si el proyecto activo tiene archivos reproyectados."""
    project_dir = prefs.get_project_dir()
    if not project_dir:
        return False
    flood_dir = project_dir / "processed" / "Flood"
    return flood_dir.exists() and any(flood_dir.glob("*.tif"))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WaterProof to Autodesk InfraWorks Converter")
        self.geometry("800x620")
        self.minsize(720, 560)
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=COLORS["bg"])

        self._build()
        self._show("start")

    def _build(self):
        # ── Tab bar ────────────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=COLORS["surface"], height=44, corner_radius=0)
        tab_bar.pack(fill="x", side="top")
        tab_bar.pack_propagate(False)

        self._tab_btns = {}
        tabs = [("start", "Start"), ("download", "Download"), ("transform", "Transform"), ("visualize", "Visualize")]
        for key, label in tabs:
            btn = ctk.CTkButton(
                tab_bar,
                text=label,
                font=(FONT["family"], FONT["size_md"]),
                fg_color="transparent",
                hover_color=COLORS["surface_alt"],
                text_color=COLORS["text_muted"],
                corner_radius=0,
                width=120,
                height=44,
                command=lambda k=key: self._show(k),
            )
            btn.pack(side="left")
            self._tab_btns[key] = btn

        # ── Logos (derecha del tab bar) ────────────────────────────────────
        LOGO_H = 28
        for filename in ("Logo_TNC.png", "Logo_WP.png"):   # TNC primero → queda más a la derecha
            img_path = APP_DIR / "ui" / "icons" / filename
            pil_img  = Image.open(img_path)
            w, h     = pil_img.size
            logo_img = ctk.CTkImage(pil_img, size=(round(w * LOGO_H / h), LOGO_H))
            ctk.CTkLabel(
                tab_bar,
                image=logo_img,
                text="",
                fg_color="transparent",
            ).pack(side="right", padx=(0, 12))

        # Estado inicial de tabs bloqueados
        if not _has_downloaded_files():
            self._set_tab_enabled("transform", False)
        if not _has_reprojected_files():
            self._set_tab_enabled("visualize", False)

        # ── Views ──────────────────────────────────────────────────────────
        self._views = {
            "start":     StartView(self, on_get_started=lambda: self._show("download")),
            "download":  DownloadView(self, on_download_complete=self.enable_transform),
            "transform": TransformView(self, on_reproject_complete=self.enable_visualize),
            "visualize": VisualizeView(self),
        }

    def _set_tab_enabled(self, key: str, enabled: bool):
        btn = self._tab_btns[key]
        btn.configure(
            state="normal" if enabled else "disabled",
            text_color=COLORS["text_muted"] if enabled else COLORS["surface_alt"],
            hover_color=COLORS["surface_alt"],
            hover=enabled,
        )

    def enable_transform(self):
        """Llamado por DownloadView al completar una descarga exitosa."""
        self._set_tab_enabled("transform", True)

    def enable_visualize(self):
        """Llamado por TransformView al completar una reproyección exitosa."""
        self._set_tab_enabled("visualize", True)

    def _show(self, key: str):
        for view in self._views.values():
            view.pack_forget()

        self._views[key].pack(fill="both", expand=True)

        for k, btn in self._tab_btns.items():
            active = k == key
            btn.configure(
                fg_color=COLORS["accent"] if active else "transparent",
                text_color=COLORS["text"] if active else COLORS["text_muted"],
            )
