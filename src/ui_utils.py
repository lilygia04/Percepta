import tkinter as tk
def rounded_rect(canvas, x1, y1, x2, y2, r=18, **kwargs):
    points = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

class Card(tk.Canvas):
    def __init__(self, master, width, height, bg="#0F1116", border="#232633", **kw):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=master["bg"], **kw)
        self.w = width
        self.h = height
        self.card_bg = bg
        self.border = border
        self._id_bg = rounded_rect(self, 2, 2, width-2, height-2, r=20, fill=bg, outline=border, width=2)

