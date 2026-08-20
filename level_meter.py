import tkinter as tk

import theme

# (Position 0-1 auf dem Balken, RGB) - Salbei bei ruhiger Sprache, Rost nahe Uebersteuerung
GRADIENT_STOPS = [
    (0.0, (0x7E, 0x94, 0x70)),
    (0.6, (0xD4, 0xA2, 0x4C)),
    (1.0, (0xA8, 0x52, 0x3A)),
]


def _color_at(t: float) -> str:
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(GRADIENT_STOPS, GRADIENT_STOPS[1:]):
        if t <= t1:
            local_t = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            rgb = (round(c0[i] + (c1[i] - c0[i]) * local_t) for i in range(3))
            return "#{:02x}{:02x}{:02x}".format(*rgb)
    return "#{:02x}{:02x}{:02x}".format(*GRADIENT_STOPS[-1][1])


class LevelMeter(tk.Canvas):
    """Pegelanzeige mit fest hinterlegtem Gruen-Gelb-Rot-Verlauf; eine Maske deckt
    den Teil rechts vom aktuellen Pegel ab, statt bei jedem Update neu zu zeichnen."""

    def __init__(self, master, width=300, height=8, segment_width=2, **kwargs):
        super().__init__(master, width=width, height=height, bg=theme.SURFACE_LIGHT,
                          highlightthickness=0, **kwargs)
        self._width = width
        self._height = height

        n_segments = max(1, width // segment_width)
        for i in range(n_segments):
            x0 = i * segment_width
            color = _color_at(x0 / width)
            self.create_rectangle(x0, 0, x0 + segment_width, height, fill=color, width=0)

        self._mask = self.create_rectangle(0, 0, width, height, fill=theme.SURFACE_LIGHT, width=0)
        self.set(0.0)

    def set(self, level: float):
        level = max(0.0, min(1.0, level))
        filled_width = self._width * level
        self.coords(self._mask, filled_width, 0, self._width, self._height)
