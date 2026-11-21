"""Graphs for Shorts and videos (owner 2026-11-21: "keep those graphs... I think that is good"). Plain, drawn into a BGR
float frame with cv2; text through space3d.ktext (plain in Shorts).

  timeline_bar(f, t, x0, x1, y, fill, a, left="BIG BANG", right="END")      progress/life bar
  curve_graph(f, t, fn, p, a, title, y0, y1, color, dashed, label)            a curve drawn on axes up to fraction p
  marker(f, x, y, a, top, bottom)                                             a tick with labels (e.g. TODAY / YOU ARE HERE)
"""
import cv2
import numpy as np

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "video"))
import space3d as X  # noqa: E402

AMBER = (66, 194, 245)
WHITE = (255, 255, 255)


def _panel(f, x0, y0, x1, y1, a):
    f[y0:y1, x0:x1] = f[y0:y1, x0:x1] * (1 - 0.72 * a) + np.array([18, 8, 4], np.float32) * 0.72 * a


def timeline_bar(f, t, x0, x1, y, fill, a, left="BIG BANG", right="END", t_in=-1.0):
    if a <= 0.01:
        return
    y = int(y)
    f[y - 22:y + 22, x0:x1] = f[y - 22:y + 22, x0:x1] * (1 - 0.16 * a) + 255 * 0.16 * a
    xf = int(x0 + (x1 - x0) * max(0.0, min(1.0, fill)))
    if xf > x0:
        f[y - 22:y + 22, x0:xf] = f[y - 22:y + 22, x0:xf] * (1 - a) + np.array(AMBER, np.float32) * a
    X.ktext(f, left, x0 + 80, y + 70, 38, WHITE, t, t_in, "Montserrat", "Bold")
    X.ktext(f, right, x1 - 40, y + 70, 38, WHITE, t, t_in, "Montserrat", "Bold")


def marker(f, t, x, y, t_in, top=None, bottom=None, top_color=AMBER):
    if t < t_in:
        return
    a = X.eo((t - t_in) / 0.2)
    x, y = int(x), int(y)
    f[y - 50:y + 50, x - 4:x + 4] = f[y - 50:y + 50, x - 4:x + 4] * (1 - a) + 255 * a
    if top:
        X.ktext(f, top, x, y + 130, 52, top_color, t, t_in)
    if bottom:
        X.ktext(f, bottom, x, y + 190, 34, WHITE, t, t_in, "Montserrat", "Bold")


def curve_graph(f, t, curves, a, title, y0, y1, t_in, x0=140, x1=None, xlabel="TIME →"):
    """curves: list of (fn(u)->0..1, progress 0..1, BGR color, dashed, label or None)."""
    if a <= 0.01:
        return
    W = f.shape[1]
    x1 = x1 or W - 140
    y0, y1 = int(y0), int(y1)
    _panel(f, x0 - 40, y1 - 90, x1 + 40, y0 + 70, a)
    lay = np.zeros_like(f)
    cv2.line(lay, (x0, y1 - 20), (x0, y0), (150, 150, 150), 3, cv2.LINE_AA)
    cv2.line(lay, (x0, y0), (x1, y0), (150, 150, 150), 3, cv2.LINE_AA)
    for fn, p, col, dashed, label in curves:
        n = int(100 * max(0.0, min(1.0, p)))
        if n < 2:
            continue
        us = np.linspace(0, n / 100, n + 1)
        pts = np.stack([x0 + (x1 - x0) * us, y0 - (y0 - y1) * np.array([fn(u) for u in us])], 1).astype(np.int32)
        if dashed:
            for k in range(0, len(pts) - 1, 4):
                cv2.line(lay, tuple(pts[k]), tuple(pts[min(k + 2, len(pts) - 1)]), col, 9, cv2.LINE_AA)
        else:
            cv2.polylines(lay, [pts], False, col, 9, cv2.LINE_AA)
        if label and p > 0.95:
            X.ktext(f, label, x1 - 120, int(pts[-1][1]) - 45, 40, col, t, t_in, "Montserrat", "Bold")
    m = (lay.sum(-1, keepdims=True) > 0).astype(np.float32) * a
    f[:] = f * (1 - m) + lay * m
    X.ktext(f, title, x0 + 230, y1 - 55, 38, WHITE, t, t_in, "Montserrat", "Bold")
    X.ktext(f, xlabel, x1 - 60, y0 + 40, 34, (180, 180, 180), t, t_in, "Montserrat", "Bold")
