"""
Vista: pantalla de bienvenida inicial.
"""
from PIL import Image
import customtkinter as ctk

from config.settings import APP_DIR
from ui.theme import COLORS, FONT


class StartView(ctk.CTkFrame):
    def __init__(self, master, on_get_started=None, **kwargs):
        super().__init__(master, fg_color=COLORS["bg"], **kwargs)
        self._on_get_started = on_get_started
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Logo ──────────────────────────────────────────────────────────────
        LOGO_H = 96
        img_path = APP_DIR / "ui" / "icons" / "Icon_WP_Autodesk.png"
        pil_img  = Image.open(img_path)
        w, h     = pil_img.size
        logo_img = ctk.CTkImage(pil_img, size=(round(w * LOGO_H / h), LOGO_H))
        ctk.CTkLabel(self, image=logo_img, text="", fg_color="transparent").grid(
            row=0, column=0, pady=(64, 24)
        )

        # ── Title ─────────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="WaterProof to Autodesk InfraWorks",
            font=(FONT["family"], FONT["size_xl"], "bold"),
            text_color=COLORS["text"],
        ).grid(row=1, column=0, pady=(0, 8))

        # ── Subtitle ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Automated spatial data pipeline for flood scenario visualization directly from WaterProof to Autodesk InfraWorks.",
            font=(FONT["family"], FONT["size_md"]),
            text_color=COLORS["text_muted"],
        ).grid(row=2, column=0, pady=(0, 48))

        # ── Steps ─────────────────────────────────────────────────────────────
        steps_frame = ctk.CTkFrame(self, fg_color="transparent")
        steps_frame.grid(row=3, column=0, padx=48, pady=(0, 48))

        steps = [
            ("01", "Download",  "Fetch flood/velocity rasters, DEM and\nportfolios from WaterProof by case ID."),
            ("02", "Transform", "Reproject all rasters to your\nAutodesk InfraWorks project CRS."),
            ("03", "Visualize", "Generate RGBA flood imagery ready\nfor Autodesk Infrawork display."),
        ]

        for i, (num, title, desc) in enumerate(steps):
            card = ctk.CTkFrame(steps_frame, fg_color=COLORS["surface"], corner_radius=8)
            card.grid(row=0, column=i, padx=(0, 0 if i == len(steps) - 1 else 16), sticky="nsew")

            ctk.CTkLabel(
                card,
                text=num,
                font=(FONT["family"], FONT["size_sm"], "bold"),
                text_color=COLORS["accent"],
            ).pack(anchor="w", padx=20, pady=(20, 4))

            ctk.CTkLabel(
                card,
                text=title,
                font=(FONT["family"], FONT["size_lg"], "bold"),
                text_color=COLORS["text"],
            ).pack(anchor="w", padx=20, pady=(0, 8))

            ctk.CTkLabel(
                card,
                text=desc,
                font=(FONT["family"], FONT["size_sm"]),
                text_color=COLORS["text_muted"],
                justify="left",
                anchor="w",
                wraplength=160,
            ).pack(anchor="w", padx=20, pady=(0, 20))

        # ── Get Started button ─────────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="Get Started",
            font=(FONT["family"], FONT["size_md"], "bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            width=200,
            height=44,
            corner_radius=6,
            command=self._on_get_started,
        ).grid(row=4, column=0, pady=(0, 64))
