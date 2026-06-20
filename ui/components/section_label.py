"""
Etiqueta de cabecera de sección: texto en mayúsculas, color muted, tamaño pequeño.
"""
import customtkinter as ctk
from ui.theme import COLORS, FONT


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text: str, **kwargs):
        super().__init__(
            master,
            text=text.upper(),
            font=(FONT["family"], FONT["size_sm"], "bold"),
            text_color=COLORS["text_muted"],
            **kwargs,
        )
