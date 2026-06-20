"""
Widget: botón de color + campo hex sincronizados.
Abre el selector de color nativo del OS al hacer clic en el cuadrado.
"""
from tkinter import colorchooser
import customtkinter as ctk
from ui.theme import COLORS, FONT


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    h = hex_str.strip().lstrip("#")
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


class ColorSwatch(ctk.CTkFrame):
    """
    Swatch de color con picker nativo y campo hex editable.

    Parámetros
    ----------
    master      : widget padre.
    initial_hex : color inicial en formato '#RRGGBB'.
    label       : texto descriptivo a la izquierda.
    on_change   : callable(hex_str) disparado al cambiar el color.
    """

    def __init__(self, master, initial_hex: str, label: str = "", on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._hex   = initial_hex.upper()
        self._on_change = on_change
        self._build(label)

    def _build(self, label: str):
        col = 0

        if label:
            ctk.CTkLabel(
                self,
                text=label,
                font=(FONT["family"], FONT["size_md"]),
                text_color=COLORS["text_muted"],
                width=90,
                anchor="w",
            ).grid(row=0, column=col, padx=(0, 8))
            col += 1

        # Cuadrado de color
        self._btn = ctk.CTkButton(
            self,
            text="",
            width=28,
            height=28,
            corner_radius=4,
            fg_color=self._hex,
            hover_color=self._hex,
            command=self._open_picker,
        )
        self._btn.grid(row=0, column=col, padx=(0, 8))
        col += 1

        # Campo hex
        self._entry = ctk.CTkEntry(
            self,
            width=80,
            height=28,
            font=(FONT["family"], FONT["size_sm"]),
            fg_color=COLORS["surface"],
            border_color=COLORS["surface_alt"],
            text_color=COLORS["text"],
            corner_radius=4,
        )
        self._entry.insert(0, self._hex)
        self._entry.grid(row=0, column=col)
        self._entry.bind("<FocusOut>", self._on_hex_entry)
        self._entry.bind("<Return>",   self._on_hex_entry)

    def _open_picker(self):
        rgb, hex_str = colorchooser.askcolor(color=self._hex, title="Select color")
        if hex_str:
            self._set(hex_str.upper())

    def _on_hex_entry(self, _event=None):
        val = self._entry.get().strip()
        if not val.startswith("#"):
            val = "#" + val
        if _hex_to_rgb(val):
            self._set(val.upper())

    def _set(self, hex_str: str):
        self._hex = hex_str
        self._btn.configure(fg_color=hex_str, hover_color=hex_str)
        self._entry.delete(0, "end")
        self._entry.insert(0, hex_str)
        if self._on_change:
            self._on_change(hex_str)

    def get(self) -> str:
        """Retorna el color actual en formato '#RRGGBB'."""
        return self._hex

    def set(self, hex_str: str):
        """Actualiza el color desde código."""
        self._set(hex_str.upper())
