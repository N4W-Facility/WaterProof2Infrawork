"""
Vista: descarga de datos desde WaterProof.
"""
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

import config.prefs as prefs
from core.downloader import check_case_exists, download_case
from ui.components.section_label import SectionLabel
from ui.theme import COLORS, FONT


class DownloadView(ctk.CTkFrame):
    def __init__(self, master, on_download_complete=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self._project_dir: Path | None = prefs.get_project_dir()
        self._on_download_complete = on_download_complete
        self._build()
        self._refresh_state()

    # ------------------------------------------------------------------ build

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Title ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Download biophysical data",
            font=(FONT["family"], FONT["size_xl"], "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=48, pady=(48, 4))

        ctk.CTkLabel(
            self,
            text="Select a project folder, enter a WaterProof case ID, and download the flood rasters.",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=48, pady=(0, 36))

        # ── Block 1: Project folder ────────────────────────────────────────
        SectionLabel(self, text="Project Folder").grid(
            row=2, column=0, sticky="w", padx=48, pady=(0, 4)
        )
        ctk.CTkLabel(self,
                text="Choose the local folder where the downloaded files will be saved. This folder will contain Flood/, Velocity/ and Raster/ subfolders.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=3, column=0, sticky="w", padx=48, pady=(0, 10))

        self._btn_new = ctk.CTkButton(
            self,
            text="+ New Project",
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            corner_radius=6,
            width=160,
            command=self._select_folder,
        )
        self._btn_new.grid(row=4, column=0, sticky="w", padx=48, pady=(0, 10))

        self._entry_path = ctk.CTkEntry(
            self,
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface"],
            border_color=COLORS["surface_alt"],
            text_color=COLORS["text_muted"],
            state="readonly",
            corner_radius=6,
            height=36,
        )
        self._entry_path.grid(row=5, column=0, sticky="ew", padx=48, pady=(0, 36))

        # ── Separator ──────────────────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=COLORS["surface_alt"]
        ).grid(row=6, column=0, sticky="ew", padx=48, pady=(0, 36))

        # ── Block 2: Case Study ────────────────────────────────────────────
        SectionLabel(self, text="Case Study").grid(
            row=7, column=0, sticky="w", padx=48, pady=(0, 4)
        )
        ctk.CTkLabel(self,
            text="Enter the numeric ID of the WaterProof case study you want to download.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=8, column=0, sticky="w", padx=48, pady=(0, 10))

        self._entry_id = ctk.CTkEntry(
            self,
            placeholder_text="e.g. 7",
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface"],
            border_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            corner_radius=6,
            height=36,
            width=240,
        )
        self._entry_id.grid(row=9, column=0, sticky="w", padx=48, pady=(0, 6))

        ctk.CTkButton(
            self,
            text="Open WaterProof ↗",
            font=(FONT["family"], FONT["size_sm"]),
            fg_color="transparent",
            hover_color=COLORS["surface"],
            text_color=COLORS["accent"],
            corner_radius=4,
            height=22,
            command=lambda: webbrowser.open("https://water-proof.org/"),
        ).grid(row=10, column=0, sticky="w", padx=44, pady=(0, 12))

        self._btn_download = ctk.CTkButton(
            self,
            text="Download",
            font=(FONT["family"], FONT["size_md"], "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            corner_radius=6,
            width=160,
            height=38,
            command=self._on_download,
        )
        self._btn_download.grid(row=11, column=0, sticky="w", padx=48, pady=(0, 16))

        self._lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["accent"],
        )
        self._lbl_status.grid(row=12, column=0, sticky="w", padx=48, pady=(0, 8))

        self._progress = ctk.CTkProgressBar(
            self,
            mode="determinate",
            progress_color=COLORS["accent"],
            fg_color=COLORS["surface_alt"],
            corner_radius=4,
            height=4,
        )
        self._progress.set(0)
        self._progress.grid(row=13, column=0, sticky="ew", padx=48, pady=(0, 48))
        self._progress.grid_remove()

    # ------------------------------------------------------------ state logic

    def _refresh_state(self):
        """Activa o desactiva el bloque de descarga según si hay carpeta."""
        has_folder = self._project_dir is not None

        # Mostrar ruta en el entry readonly
        self._entry_path.configure(state="normal")
        self._entry_path.delete(0, "end")
        if has_folder:
            self._entry_path.insert(0, str(self._project_dir))
        self._entry_path.configure(state="readonly")

        # Habilitar / deshabilitar bloque Case Study
        state = "normal" if has_folder else "disabled"
        entry_color = COLORS["surface"] if has_folder else COLORS["surface_alt"]
        btn_color   = COLORS["accent"]   if has_folder else COLORS["surface_alt"]
        text_color  = COLORS["text"]     if has_folder else COLORS["text_muted"]

        self._entry_id.configure(
            state=state,
            fg_color=entry_color,
            text_color=text_color,
        )
        self._btn_download.configure(
            state=state,
            fg_color=btn_color,
        )

    def _set_status(self, message: str, error: bool = False):
        color = COLORS["error"] if error else COLORS["accent"]
        self._lbl_status.configure(text=message, text_color=color)

    # ---------------------------------------------------------------- actions

    def _select_folder(self):
        path = filedialog.askdirectory(title="Select project folder")
        if not path:
            return
        self._project_dir = Path(path)
        prefs.set_project_dir(self._project_dir)
        self._refresh_state()
        self._set_status("")

    def _on_download(self):
        raw_id = self._entry_id.get().strip()
        if not raw_id:
            self._set_status("Please enter a case study ID.", error=True)
            return
        if not raw_id.isdigit():
            self._set_status("Case ID must be a number.", error=True)
            return

        case_id = int(raw_id)
        self._btn_download.configure(state="disabled", text="Checking...")
        self._set_status("")
        threading.Thread(target=self._run_download, args=(case_id,), daemon=True).start()

    def _run_download(self, case_id: int):
        # Validar existencia antes de descargar
        if not check_case_exists(case_id):
            self.after(0, lambda: self._set_status(
                f"Case ID {case_id} was not found on WaterProof.", error=True
            ))
            self.after(0, lambda: self._btn_download.configure(
                state="normal", text="Download"
            ))
            return

        self.after(0, lambda: self._btn_download.configure(text="Downloading..."))
        self.after(0, lambda: self._set_status("Downloading files, please wait..."))
        self.after(0, lambda: [self._progress.set(0), self._progress.grid()])

        def progress(current, total):
            self.after(0, lambda: self._progress.set(current / total))

        try:
            result = download_case(case_id, self._project_dir, progress_cb=progress)
            total = len(result["flood"]) + len(result["velocity"]) + 1
            msg = f"Done. {total} files saved to {self._project_dir}"
            self.after(0, lambda: self._set_status(msg))
            if self._on_download_complete:
                self.after(0, self._on_download_complete)
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", error=True))
        finally:
            self.after(0, lambda: self._btn_download.configure(
                state="normal", text="Download"
            ))
            self.after(0, self._progress.grid_remove)
