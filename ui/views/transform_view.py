"""
Vista: reproyección de rasters al CRS del proyecto InfraWorks.
"""
import threading
from pathlib import Path

import customtkinter as ctk

import config.prefs as prefs
from core.transformer import search_crs, reproject_case
from ui.components.section_label import SectionLabel
from ui.theme import COLORS, FONT


class TransformView(ctk.CTkFrame):
    def __init__(self, master, on_reproject_complete=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self._selected_crs: str | None = prefs.get_last_crs()
        self._on_reproject_complete = on_reproject_complete
        self._build()
        self._restore_state()

    # ------------------------------------------------------------------ build

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Title ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Reproject Rasters",
            font=(FONT["family"], FONT["size_xl"], "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=48, pady=(48, 4))

        ctk.CTkLabel(
            self,
            text="Search the coordinate system you selected in InfraWorks and reproject all downloaded rasters to match it.",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=48, pady=(0, 36))

        # ── Block 1: CRS Search ────────────────────────────────────────────
        SectionLabel(self, text="Coordinate System").grid(
            row=2, column=0, sticky="w", padx=48, pady=(0, 4)
        )
        ctk.CTkLabel(self,
            text="Open InfraWorks, go to Project Settings → Coordinate System, and note the name shown there. Type that name here and click Search. Select the matching result from the list.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=3, column=0, sticky="w", padx=48, pady=(0, 10))

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=4, column=0, sticky="w", padx=48, pady=(0, 10))

        self._entry_crs = ctk.CTkEntry(
            search_row,
            placeholder_text="Type the name shown in InfraWorks (e.g. MAGNA, Colombia, UTM)...",
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface"],
            border_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            corner_radius=6,
            height=36,
            width=380,
        )
        self._entry_crs.pack(side="left", padx=(0, 10))
        self._entry_crs.bind("<Return>", lambda e: self._on_search())

        self._btn_search = ctk.CTkButton(
            search_row,
            text="Search",
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface_alt"],
            hover_color=COLORS["accent"],
            text_color=COLORS["text"],
            corner_radius=6,
            width=90,
            height=36,
            command=self._on_search,
        )
        self._btn_search.pack(side="left")

        # Resultados
        self._results_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["surface"],
            corner_radius=6,
            height=160,
        )
        self._results_frame.grid(
            row=5, column=0, sticky="ew", padx=48, pady=(0, 12)
        )
        self._results_frame.columnconfigure(0, weight=1)
        self._results_frame.grid_remove()

        # Label de confirmación
        self._lbl_selected = ctk.CTkLabel(
            self,
            text="",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["accent"],
            anchor="w",
        )
        self._lbl_selected.grid(row=6, column=0, sticky="w", padx=48, pady=(0, 28))

        # ── Separator ──────────────────────────────────────────────────────
        ctk.CTkFrame(
            self, height=1, fg_color=COLORS["surface_alt"]
        ).grid(row=7, column=0, sticky="ew", padx=48, pady=(0, 28))

        # ── Block 2: Reproject ─────────────────────────────────────────────
        SectionLabel(self, text="Project").grid(
            row=8, column=0, sticky="w", padx=48, pady=(0, 4)
        )
        ctk.CTkLabel(self,
            text="Once the coordinate system is selected, click Reproject All. The reprojected rasters will be saved to the processed/ folder inside your project, keeping the same file structure.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=9, column=0, sticky="w", padx=48, pady=(0, 10))

        self._lbl_project = ctk.CTkLabel(
            self,
            text="No project selected.",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self._lbl_project.grid(row=10, column=0, sticky="w", padx=48, pady=(0, 16))

        self._btn_reproject = ctk.CTkButton(
            self,
            text="Reproject All",
            font=(FONT["family"], FONT["size_md"], "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            corner_radius=6,
            width=160,
            height=38,
            command=self._on_reproject,
        )
        self._btn_reproject.grid(row=11, column=0, sticky="w", padx=48, pady=(0, 16))

        self._lbl_status = ctk.CTkLabel(
            self,
            text="",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["accent"],
            anchor="w",
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

    def _restore_state(self):
        if self._selected_crs:
            self._lbl_selected.configure(text=f"Selected: {self._selected_crs}")

        project_dir = prefs.get_project_dir()
        if project_dir:
            self._lbl_project.configure(
                text=str(project_dir), text_color=COLORS["text"]
            )

        self._refresh_reproject_btn()

    def _refresh_reproject_btn(self):
        has_crs     = self._selected_crs is not None
        has_project = prefs.get_project_dir() is not None
        enabled     = has_crs and has_project
        self._btn_reproject.configure(
            state="normal" if enabled else "disabled",
            fg_color=COLORS["accent"] if enabled else COLORS["surface_alt"],
        )

    def _set_status(self, message: str, error: bool = False):
        color = COLORS["error"] if error else COLORS["accent"]
        self._lbl_status.configure(text=message, text_color=color)

    # ---------------------------------------------------------------- actions

    def _on_search(self):
        query = self._entry_crs.get().strip()
        if not query:
            return

        results = search_crs(query)

        for w in self._results_frame.winfo_children():
            w.destroy()

        self._results_frame.grid()

        if not results:
            ctk.CTkLabel(
                self._results_frame,
                text="No results found.",
                font=(FONT["family"], FONT["size_md"]),
                text_color=COLORS["text_muted"],
            ).grid(row=0, column=0, sticky="w", padx=12, pady=8)
            return

        for i, r in enumerate(results):
            label = f"{r['crs_str']}   {r['name']}"
            ctk.CTkButton(
                self._results_frame,
                text=label,
                font=(FONT["family"], FONT["size_md"]),
                fg_color="transparent",
                hover_color=COLORS["surface_alt"],
                text_color=COLORS["text"],
                anchor="w",
                corner_radius=4,
                command=lambda crs=r["crs_str"], name=r["name"]: self._select_crs(crs, name),
            ).grid(row=i, column=0, sticky="ew", padx=4, pady=2)

    def _select_crs(self, crs_str: str, name: str):
        self._selected_crs = crs_str
        prefs.set_last_crs(crs_str)
        self._lbl_selected.configure(text=f"Selected: {crs_str} — {name}")
        self._results_frame.grid_remove()
        self._refresh_reproject_btn()

    def _on_reproject(self):
        project_dir = prefs.get_project_dir()
        if not project_dir:
            self._set_status("Select a project folder first.", error=True)
            return

        self._btn_reproject.configure(state="disabled", text="Reprojecting...")
        self._set_status("")
        self._progress.set(0)
        self._progress.grid()
        threading.Thread(
            target=self._run_reproject,
            args=(project_dir,),
            daemon=True,
        ).start()

    def _run_reproject(self, project_dir: Path):
        def progress(current, total):
            self.after(0, lambda: self._set_status(f"Reprojecting {current}/{total}..."))
            self.after(0, lambda: self._progress.set(current / total))

        try:
            result = reproject_case(project_dir, self._selected_crs, progress)
            out_path = project_dir / "processed"
            self.after(0, lambda: self._set_status(
                f"Done. {len(result)} files saved to {out_path}"
            ))
            if self._on_reproject_complete:
                self.after(0, self._on_reproject_complete)
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", error=True))
        finally:
            self.after(0, lambda: self._btn_reproject.configure(
                state="normal", text="Reproject All"
            ))
            self.after(0, self._progress.grid_remove)
