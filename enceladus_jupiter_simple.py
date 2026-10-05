#!/usr/bin/env python3
"""Enceladus transit of Jupiter - minimal deep-space render.

Scientific cues (Cassini): high-albedo ice surface, young south polar
terrain with tiger-stripe fractures and H2O jets, warm cream zones and
belt/zone banding on Jupiter, distant sun upper-left.
"""
import math
import random
import sys

sys.path.insert(0, "/tmp/opencode")
from ascii_arcade_wallpaper import W, H, fill_rect, draw_text, write_png  # noqa: E402

OUT = "/home/anontokoy/Pictures/enceladus-jupiter-2560x1600.png"
LIGHT = (-0.50, -0.28, 0.82)

JUP_BANDS = [
    (0.00, (120, 72, 46)), (0.07, (168, 108, 64)), (0.16, (214, 178, 132)),
    (0.26, (188, 140, 92)), (0.36, (230, 210, 178)), (0.48, (172, 118, 74)),
    (0.58, (208, 170, 122)), (0.68, (150, 94, 58)), (0.78, (226, 200, 164)),
    (0.88, (182, 128, 82)), (1.00, (120, 72, 46)),
]
ICE_STOPS = [
    (16, 15, 14), (42, 40, 38), (82, 80, 76), (128, 125, 118),
    (178, 173, 162), (218, 211, 196), (246, 241, 228),
]
CRATERS = [
    (-0.35, -0.45, 0.14, 0.07), (0.05, -0.60, 0.10, 0.05),
    (-0.60, -0.12, 0.11, 0.05), (0.28, -0.26, 0.09, 0.045),
    (0.52, -0.48, 0.12, 0.05), (-0.15, -0.20, 0.07, 0.035),
]
STRIPES = (0.42, 0.55, 0.68, 0.81)


def interp(stops, t):
    t = min(1.0, max(0.0, t)) * (len(stops) - 1)
    i = int(t)
    if i >= len(stops) - 1:
        return stops[-1]
    f = t - i
    a, b = stops[i], stops[i + 1]
    return (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f),
            int(a[2] + (b[2] - a[2]) * f))


def band_color(t):
    if t <= JUP_BANDS[0][0]:
        return JUP_BANDS[0][1]
    for i in range(1, len(JUP_BANDS)):
        lim, c = JUP_BANDS[i]
        if t <= lim:
            l0, c0 = JUP_BANDS[i - 1]
            f = (t - l0) / (lim - l0)
            return (c0[0] + (c[0] - c0[0]) * f, c0[1] + (c[1] - c0[1]) * f,
                    c0[2] + (c[2] - c0[2]) * f)
    return JUP_BANDS[-1][1]


def scale(c, f):
    return (min(255, int(c[0] * f)), min(255, int(c[1] * f)),
            min(255, int(c[2] * f)))


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def blend_rect(fb, x, y, w, h, color, a):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    ia = 1.0 - a
    for yy in range(y0, y1):
        base = yy * W * 3
        for xx in range(x0, x1):
            i = base + xx * 3
            fb[i] = int(fb[i] * ia + color[0] * a)
            fb[i + 1] = int(fb[i + 1] * ia + color[1] * a)
            fb[i + 2] = int(fb[i + 2] * ia + color[2] * a)


def hash01(x, y):
    return (((x * 73856093) ^ (y * 19349663)) & 0xffff) / 65535.0


def gas_giant(fb, cx, cy, r, tilt):
    lx, ly, lz = LIGHT
    ct, st = math.cos(tilt), math.sin(tilt)
    step = 5
    for gy in range(0, H, step):
        for gx in range(0, W, step):
            px = gx + step / 2
            py = gy + step / 2
            dx = (px - cx) / r
            dy = (py - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz) ** 1.15
            by = dx * st + dy * ct
            warp = 0.010 * math.sin(dx * 7.0) + 0.006 * math.sin(dx * 17.0 + dy * 3.0)
            base = band_color(by + 0.5 + warp)
            f = (0.30 + 0.90 * v) * (0.96 + 0.06 * hash01(gx // step, gy // step))
            storm = ((px - 1780) / 70.0) ** 2 + ((py - 1030) / 36.0) ** 2
            if storm < 1.0:
                base = mix(base, (246, 238, 224), 0.45 * (1.0 - storm))
                f *= 1.04
            fill_rect(fb, gx, gy, step, step, scale(base, f))


def moon(fb, cx, cy, r, craters=True, ambient=0.0):
    lx, ly, lz = LIGHT
    step = 5
    for gy in range(0, H, step):
        for gx in range(0, W, step):
            px = gx + step / 2
            py = gy + step / 2
            dx = (px - cx) / r
            dy = (py - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz)
            v = ambient + (1.0 - ambient) * v
            mott = (0.60 * math.sin(dx * 17.0 + 1.3) * math.sin(dy * 19.0 - 0.7)
                    + 0.40 * math.sin(dx * 37.0 - dy * 29.0))
            v += 0.015 * mott
            for ccx, ccy, crad, cdepth in CRATERS:
                cd = ((dx - ccx) ** 2 + (dy - ccy) ** 2) / (crad * crad)
                if cd < 1.0:
                    v -= cdepth * math.exp(-2.0 * cd)
            stripe = 0.0
            if dy > 0.30:
                ss = dy + 0.045 * math.sin(dx * 3.1 + 0.8)
                for sc in STRIPES:
                    dd = abs(ss - sc)
                    if dd < 0.022:
                        stripe = 1.0 - dd / 0.022
                        break
            v -= 0.09 * stripe
            v = min(1.0, max(0.0, v))
            col = interp(ICE_STOPS, v)
            if stripe > 0.0:
                col = mix(col, (112, 142, 168), 0.28 * stripe)
            fill_rect(fb, gx, gy, step, step, col)


def plume(fb, cx, cy, r):
    rng = random.Random(42)
    for j in range(24):
        ang = math.radians(56 + (j + 0.5) * (68.0 / 24.0))
        ux, uy = math.cos(ang), math.sin(ang)
        ppx, ppy = -uy, ux
        bx, by = cx + ux * (r - 4), cy + uy * (r - 4)
        length = rng.uniform(280.0, 560.0)
        tilt = rng.uniform(-0.25, 0.25)
        n = int(length / 5)
        for i in range(n):
            t = i / n
            d = t * length
            off = (tilt + rng.uniform(-0.05, 0.05)) * d
            x = bx + ux * d + ppx * off + rng.uniform(-4, 4)
            y = by + uy * d + ppy * off + rng.uniform(-4, 4)
            a = ((1.0 - t) * 0.36 + 0.02) * (1.05 - 0.45 * ux)
            sz = 3 if t < 0.4 else 2
            blend_rect(fb, int(x), int(y), sz, sz, (208, 222, 236), min(0.6, a))
    for _ in range(900):
        t = rng.random() ** 0.7
        ang = math.radians(50 + rng.random() * 80)
        ux, uy = math.cos(ang), math.sin(ang)
        d = t * 620.0
        x = cx + ux * (r + d) + rng.gauss(0, 22 * t + 4)
        y = cy + uy * (r + d) + rng.gauss(0, 22 * t + 4)
        a = 0.055 * (1.0 - t) * (1.05 - 0.45 * ux)
        blend_rect(fb, int(x), int(y), 3, 3, (200, 216, 232), max(0.0, a))


def main():
    fb = bytearray(W * H * 3)
    for y in range(H):
        t = y / H
        b = 5 + int(2 * t)
        fill_rect(fb, 0, y, W, 1, (b - 4, b - 3, b))

    rng = random.Random(11)
    for _ in range(650):
        sx = rng.randrange(0, W - 5)
        sy = rng.randrange(0, 1500)
        b = rng.choice([45, 70, 105, 150, 205, 255])
        size = 2 if b < 100 else (3 if b < 200 else 4)
        tint = rng.choice([(0, 0, 15), (0, 5, 20), (0, 0, 0), (15, 5, -10)])
        col = (min(255, b + tint[0]), min(255, b + tint[1]), min(255, b + tint[2]))
        fill_rect(fb, sx, sy, size, size, col)

    for _ in range(700):
        t = rng.random()
        x = int(40 + t * 300 + rng.gauss(0, 55))
        y = int(t * 1560)
        b = rng.choice([28, 38, 50, 62])
        fill_rect(fb, x, y, 2, 2, (b, b + 5, b + 14))

    for fx, fy in ((170, 900), (330, 1450), (95, 1390)):
        blend_rect(fb, fx - 11, fy - 11, 23, 23, (150, 165, 185), 0.10)
        blend_rect(fb, fx - 5, fy - 5, 11, 11, (210, 220, 235), 0.35)
        fill_rect(fb, fx, fy, 3, 3, (245, 248, 252))

    for ddy in range(-30, 31):
        for ddx in range(-30, 31):
            dd = math.hypot(ddx, ddy)
            if dd <= 30:
                blend_rect(fb, 108 + ddx, 330 + ddy, 1, 1, (255, 246, 218),
                           0.30 * math.exp(-dd / 7.5))
    fill_rect(fb, 106, 328, 5, 5, (255, 252, 240))

    gas_giant(fb, 1950, 150, 1750, math.radians(-8))
    moon(fb, 980, 780, 430)
    plume(fb, 980, 780, 430)

    draw_text(fb, "ENCELADUS / JUPITER", 40, 1528, 4, (105, 112, 122))
    blend_rect(fb, 1400, 1424, 232, 40, (3, 5, 8), 0.55)
    draw_text(fb, "H2O PLUME", 1410, 1432, 4, (150, 160, 172))
    draw_text(fb, '-', 1352, 1444, 4, (110, 120, 132))

    dim = bytes(int(i * 0.95) for i in range(256))
    for y in range(2, H, 3):
        st = y * W * 3
        fb[st:st + W * 3] = fb[st:st + W * 3].translate(dim)

    write_png(OUT, fb)
    print("written", OUT, W, "x", H)


if __name__ == '__main__':
    main()
