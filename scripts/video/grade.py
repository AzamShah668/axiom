"""Per-video colour grade for the v3 style: one colour world per episode, applied to footage only (graphics keep
their own colours).

  g = Grade(**edit["grade"]);  frame = g(frame, f)        (BGR uint8 1920x1080, f = frame number for the grain)

Parameters (edit.base.json "grade"):
  preset    "amber_teal" (default: teal shadows, amber highlights - black holes, stars), "gold" (Sun, fire),
            "ice" (cold blue - planets, ice moons), "neutral"
  contrast  S-curve strength (0 = none, 0.25 = default)
  sat       saturation multiplier (1.3 default; measured on the reference: median HSV saturation 193 vs our 93)
  vignette  corner darkening, 0-1 (0.35 = corners about 1 stop darker)
  grain     film grain strength in 8-bit levels (3 default; 0 = off)
  lift      black level lift (0.0-0.05) so deep space keeps detail
"""
import numpy as np, cv2

W, H = 1920, 1080

PRESETS = {  # split-tone: (shadow tint BGR, highlight tint BGR), amount; true black stays black
    "amber_teal": ((16, 8, -8), (-18, 4, 20), 1.0),
    "gold": ((-4, 2, 8), (-28, 2, 24), 1.0),
    "ice": ((16, 6, -8), (10, 4, -8), 1.0),
    "neutral": ((0, 0, 0), (0, 0, 0), 0.0),
}


class Grade:
    def __init__(self, preset="amber_teal", contrast=0.25, sat=1.3, vignette=0.35, grain=3.0, lift=0.01, **_):
        sh, hi, amt = PRESETS.get(preset, PRESETS["amber_teal"])
        x = np.arange(256) / 255.0
        s = x + contrast * (x - 0.5) * (1 - np.abs(2 * x - 1)) * 2       # gentle S around mid grey
        s = lift + (1 - lift) * np.clip(s, 0, 1)
        w_sh = np.clip(x / 0.12, 0, 1) * np.clip(1 - (x - 0.12) / 0.33, 0, 1)  # tint weights by input level
        w_hi = np.clip((x - 0.5) / 0.5, 0, 1) ** 1.2
        self.lut = np.stack([np.clip(255 * s + amt * (sh[c] * w_sh + hi[c] * w_hi), 0, 255)
                             for c in range(3)], 1).astype(np.uint8)[:, None, :]  # (256, 1, 3) for cv2.LUT
        self.sat = sat
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        v = 1 - vignette * np.clip(d / 2, 0, 1) ** 1.4 * 1.6
        self.vig = np.repeat((np.clip(v, 0, 1) * 255).astype(np.uint8)[..., None], 3, 2) if vignette else None
        self.grain = None
        if grain:  # monochrome grain, 4 frames cycled (int16, added with saturation)
            r = np.random.default_rng(5)
            self.grain = [np.repeat(cv2.resize(cv2.GaussianBlur(r.normal(0, grain, (H // 2, W // 2)).astype(np.float32), (0, 0), 0.6),
                                               (W, H), interpolation=cv2.INTER_NEAREST).round().astype(np.int16)[..., None], 3, 2)
                          for _ in range(4)]

    def __call__(self, fr, f=0):
        out = cv2.LUT(fr, self.lut)
        if self.sat != 1.0:
            g = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            out = cv2.addWeighted(out, self.sat, g, 1 - self.sat, 0)
        if self.vig is not None:
            out = cv2.multiply(out, self.vig, scale=1 / 255)
        if self.grain is not None:
            out = cv2.add(out, self.grain[f % len(self.grain)], dtype=cv2.CV_8U)
        return out
