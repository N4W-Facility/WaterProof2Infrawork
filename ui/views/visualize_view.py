"""
Vista: generación de imágenes RGBA de inundación con controles de color.
"""
import threading
from pathlib import Path

import customtkinter as ctk

import config.prefs as prefs
from core.visualizer import (
    scan_global_stats, generate_all,
    DEFAULT_ANCHOR_COLORS, DEFAULT_DANGER_COLOR,
    DEFAULT_VEL_INTENSITY, DEFAULT_VEL_THRESHOLD, DEFAULT_DRY_THRESH,
)
from ui.components.color_swatch import ColorSwatch
from ui.components.section_label import SectionLabel
from ui.theme import COLORS, FONT

_ANCHOR_LABELS = ["Very shallow", "Ankle", "Waist", "Chest", "Extreme"]


class VisualizeView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self._stats: dict | None = None
        self._build()

    # ------------------------------------------------------------------ build

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Title ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Visualize Flood Maps",
            font=(FONT["family"], FONT["size_xl"], "bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=48, pady=(48, 4))

        ctk.CTkLabel(
            self,
            text="Scan rasters to compute global color ranges, adjust the style, then generate one RGBA image per Flood–Velocity pair.",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
        ).grid(row=1, column=0, sticky="w", padx=48, pady=(0, 32))

        # ── Scrollable content ─────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        scroll.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        scroll.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        row = 0

        # ── Block 1: Scan ──────────────────────────────────────────────────
        SectionLabel(scroll, text="Color Range").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)
        ); row += 1
        ctk.CTkLabel(scroll,
            text="Scan all rasters to compute the global depth and velocity ranges. These values define the color scale so all images are comparable with each other.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        self._btn_scan = ctk.CTkButton(
            scroll, text="Scan Ranges",
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface_alt"], hover_color=COLORS["accent"],
            text_color=COLORS["text"], corner_radius=6, width=140, height=36,
            command=self._on_scan,
        )
        self._btn_scan.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 6)); row += 1

        self._progress_scan = ctk.CTkProgressBar(scroll,
            mode="determinate", progress_color=COLORS["accent"],
            fg_color=COLORS["surface_alt"], corner_radius=4, height=4)
        self._progress_scan.set(0)
        self._progress_scan.grid(row=row, column=0, sticky="ew", padx=48, pady=(0, 10))
        self._progress_scan.grid_remove(); row += 1

        self._lbl_depth = ctk.CTkLabel(scroll, text="Depth:    —",
            font=(FONT["family"], FONT["size_md"]), text_color=COLORS["text_muted"], anchor="w")
        self._lbl_depth.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 2)); row += 1

        self._lbl_vel = ctk.CTkLabel(scroll, text="Velocity: —",
            font=(FONT["family"], FONT["size_md"]), text_color=COLORS["text_muted"], anchor="w")
        self._lbl_vel.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 24)); row += 1

        # ── Separator ──────────────────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["surface_alt"]).grid(
            row=row, column=0, sticky="ew", padx=48, pady=(0, 24)); row += 1

        # ── Block 2: Depth color anchors ───────────────────────────────────
        SectionLabel(scroll, text="Depth Color Gradient").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1
        ctk.CTkLabel(scroll,
            text="Define the 5 colors of the depth gradient, from shallowest to deepest. Click the color square to open the color picker, or type a hex code directly.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        self._anchor_swatches: list[ColorSwatch] = []
        for label, default_hex in zip(_ANCHOR_LABELS, DEFAULT_ANCHOR_COLORS):
            sw = ColorSwatch(scroll, initial_hex=default_hex, label=label)
            sw.grid(row=row, column=0, sticky="w", padx=48, pady=3)
            self._anchor_swatches.append(sw)
            row += 1

        # ── Block 3: Velocity tint ─────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["surface_alt"]).grid(
            row=row, column=0, sticky="ew", padx=48, pady=(16, 16)); row += 1

        SectionLabel(scroll, text="Velocity Tint").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1
        ctk.CTkLabel(scroll,
            text="High-velocity areas are blended with a danger color to highlight fast-moving water. Set the color and how strong the blend is (0 = no tint, 1 = maximum).",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        self._danger_swatch = ColorSwatch(scroll, initial_hex=DEFAULT_DANGER_COLOR, label="Danger color")
        self._danger_swatch.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 12)); row += 1

        intensity_row = ctk.CTkFrame(scroll, fg_color="transparent")
        intensity_row.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1

        ctk.CTkLabel(intensity_row, text="Intensity",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"], width=90, anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._slider_intensity = ctk.CTkSlider(
            intensity_row,
            from_=0, to=1,
            number_of_steps=20,
            progress_color=COLORS["accent"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            fg_color=COLORS["surface_alt"],
            width=200,
            command=self._on_intensity_change,
        )
        self._slider_intensity.set(DEFAULT_VEL_INTENSITY)
        self._slider_intensity.pack(side="left", padx=(0, 10))

        self._lbl_intensity = ctk.CTkLabel(intensity_row,
            text=f"{DEFAULT_VEL_INTENSITY:.2f}",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text"],
        )
        self._lbl_intensity.pack(side="left")

        # ── Block 4: Depth range ───────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["surface_alt"]).grid(
            row=row, column=0, sticky="ew", padx=48, pady=(16, 16)); row += 1

        SectionLabel(scroll, text="Depth Range (m)").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1
        ctk.CTkLabel(scroll,
            text="Min threshold: pixels below this depth are transparent (dry). \nDisplay max: depths above this value will all map to the darkest color. Both are pre-filled by the scan.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        depth_row = ctk.CTkFrame(scroll, fg_color="transparent")
        depth_row.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1

        self._entry_depth_min = self._num_entry(depth_row, "Min threshold", str(DEFAULT_DRY_THRESH))
        self._entry_depth_max = self._num_entry(depth_row, "Display max", "—")

        # ── Block 5: Velocity range ────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["surface_alt"]).grid(
            row=row, column=0, sticky="ew", padx=48, pady=(16, 16)); row += 1

        SectionLabel(scroll, text="Velocity Range (m/s)").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1
        ctk.CTkLabel(scroll,
            text="Threshold: pixels below this velocity receive no danger tint — only pure depth color. Display max: velocities above this value show the full tint intensity.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        vel_row = ctk.CTkFrame(scroll, fg_color="transparent")
        vel_row.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1

        self._entry_vel_threshold = self._num_entry(vel_row, "Threshold", f"{DEFAULT_VEL_THRESHOLD:.2f}")
        self._entry_vel_max = self._num_entry(vel_row, "Display max", "—")

        # ── Block 6: Generate ──────────────────────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color=COLORS["surface_alt"]).grid(
            row=row, column=0, sticky="ew", padx=48, pady=(16, 16)); row += 1

        SectionLabel(scroll, text="Output").grid(
            row=row, column=0, sticky="w", padx=48, pady=(0, 4)); row += 1
        ctk.CTkLabel(scroll,
            text="Generates one RGBA GeoTIFF per Flood–Velocity pair (30 files total). Output is saved to the visualize/ folder inside your project. You can load these files directly in QGIS or InfraWorks.",
            font=(FONT["family"], FONT["size_sm"]), text_color=COLORS["text_muted"], anchor="w", justify="left", wraplength=700,
        ).grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        self._btn_generate = ctk.CTkButton(
            scroll, text="Generate All RGBA",
            font=(FONT["family"], FONT["size_md"], "bold"),
            fg_color=COLORS["surface_alt"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_muted"], corner_radius=6,
            width=180, height=38, state="disabled",
            command=self._on_generate,
        )
        self._btn_generate.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 16)); row += 1

        self._lbl_status = ctk.CTkLabel(scroll, text="",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["accent"], anchor="w")
        self._lbl_status.grid(row=row, column=0, sticky="w", padx=48, pady=(0, 8)); row += 1

        self._progress = ctk.CTkProgressBar(scroll,
            mode="determinate", progress_color=COLORS["accent"],
            fg_color=COLORS["surface_alt"], corner_radius=4, height=4)
        self._progress.set(0)
        self._progress.grid(row=row, column=0, sticky="ew", padx=48, pady=(0, 48))
        self._progress.grid_remove()

    # ─────────────────────────── helpers ──────────────────────────────────────

    def _num_entry(self, parent, label: str, default: str) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=(0, 24))
        ctk.CTkLabel(frame, text=label,
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w")
        entry = ctk.CTkEntry(frame, width=90, height=30,
            font=(FONT["family"], FONT["size_md"]),
            fg_color=COLORS["surface"], border_color=COLORS["surface_alt"],
            text_color=COLORS["text"], corner_radius=4)
        entry.insert(0, default)
        entry.pack()
        return entry

    def _get_float(self, entry: ctk.CTkEntry, fallback: float) -> float:
        try:
            return float(entry.get())
        except ValueError:
            return fallback

    # ─────────────────────────── state ────────────────────────────────────────

    def _set_status(self, message: str, error: bool = False):
        color = COLORS["error"] if error else COLORS["accent"]
        self._lbl_status.configure(text=message, text_color=color)

    def _enable_generate(self):
        self._btn_generate.configure(
            state="normal", fg_color=COLORS["accent"],
            text_color=COLORS["text"], hover_color=COLORS["accent_hover"],
        )

    def _on_intensity_change(self, value):
        self._lbl_intensity.configure(text=f"{value:.2f}")

    def _current_params(self) -> dict:
        return {
            "anchor_colors": [sw.get() for sw in self._anchor_swatches],
            "danger_color":  self._danger_swatch.get(),
            "vel_intensity":  self._slider_intensity.get(),
            "vel_threshold":  self._get_float(self._entry_vel_threshold, DEFAULT_VEL_THRESHOLD),
            "dry_thresh":     self._get_float(self._entry_depth_min, DEFAULT_DRY_THRESH),
            "depth_max_override": self._get_float(self._entry_depth_max, None) if self._entry_depth_max.get() not in ("—", "") else None,
            "vel_max_override":   self._get_float(self._entry_vel_max,   None) if self._entry_vel_max.get()   not in ("—", "") else None,
        }

    def _effective_stats(self, params: dict) -> dict:
        stats = dict(self._stats)
        if params["depth_max_override"] is not None:
            stats["depth_max"] = params["depth_max_override"]
        if params["vel_max_override"] is not None:
            stats["vel_max"] = params["vel_max_override"]
        stats["depth_min"] = params["dry_thresh"]
        return stats

    # ─────────────────────────── actions ──────────────────────────────────────

    def _on_scan(self):
        project_dir = prefs.get_project_dir()
        if not project_dir:
            self._set_status("No project folder selected.", error=True)
            return
        processed_dir = project_dir / "processed"
        if not processed_dir.exists():
            self._set_status("No reprojected files found. Run Transform first.", error=True)
            return

        self._btn_scan.configure(state="disabled", text="Scanning...")
        self._progress_scan.set(0)
        self._progress_scan.grid()
        self._set_status("")
        threading.Thread(target=self._run_scan, args=(processed_dir,), daemon=True).start()

    def _run_scan(self, processed_dir: Path):
        dry = self._get_float(self._entry_depth_min, DEFAULT_DRY_THRESH)

        def progress(c, t):
            self.after(0, lambda: self._progress_scan.set(c / t))
            self.after(0, lambda: self._set_status(f"Scanning {c}/{t}..."))

        try:
            stats = scan_global_stats(processed_dir, progress, dry_thresh=dry)
            self._stats = stats
            self.after(0, lambda: self._lbl_depth.configure(
                text=f"Depth:    {stats['depth_min']:.3f} – {stats['depth_max']:.3f} m",
                text_color=COLORS["text"]))
            self.after(0, lambda: self._lbl_vel.configure(
                text=f"Velocity: {stats['vel_min']:.3f} – {stats['vel_max']:.3f} m/s",
                text_color=COLORS["text"]))
            # Poblar campos editables con valores del scan
            self.after(0, lambda: self._set_entry(self._entry_depth_max, f"{stats['depth_max']:.3f}"))
            self.after(0, lambda: self._set_entry(self._entry_vel_max,   f"{stats['vel_max']:.3f}"))
            self.after(0, lambda: self._set_status("Ranges computed. Ready to generate."))
            self.after(0, self._enable_generate)
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", error=True))
        finally:
            self.after(0, lambda: self._btn_scan.configure(state="normal", text="Scan Ranges"))
            self.after(0, self._progress_scan.grid_remove)

    def _set_entry(self, entry: ctk.CTkEntry, value: str):
        entry.delete(0, "end")
        entry.insert(0, value)

    def _on_generate(self):
        project_dir = prefs.get_project_dir()
        if not project_dir or self._stats is None:
            return

        self._btn_generate.configure(state="disabled", text="Generating...")
        self._progress.set(0)
        self._progress.grid()
        self._set_status("")

        params = self._current_params()
        threading.Thread(
            target=self._run_generate,
            args=(project_dir / "processed", params),
            daemon=True,
        ).start()

    def _run_generate(self, processed_dir: Path, params: dict):
        stats = self._effective_stats(params)

        def progress(c, t):
            self.after(0, lambda: self._progress.set(c / t))
            self.after(0, lambda: self._set_status(f"Generating {c}/{t}..."))

        try:
            results = generate_all(
                processed_dir, stats,
                anchor_colors=params["anchor_colors"],
                danger_color=params["danger_color"],
                vel_intensity=params["vel_intensity"],
                vel_threshold=params["vel_threshold"],
                dry_thresh=params["dry_thresh"],
                progress_cb=progress,
            )
            out_dir = processed_dir.parent / "visualize"
            self.after(0, lambda: self._set_status(
                f"Done. {len(results)} RGBA files saved to {out_dir}"
            ))
        except Exception as e:
            self.after(0, lambda: self._set_status(f"Error: {e}", error=True))
        finally:
            self.after(0, lambda: self._btn_generate.configure(
                state="normal", text="Generate All RGBA"))
            self.after(0, self._progress.grid_remove)
