#!/usr/bin/env python3
"""Wide deep-space view of the Saturnian system with Jupiter in the distance.

Moon surface cues from Cassini literature:
  Enceladus - tiger stripes + H2O plume (ISS/INMS/UVIS papers)
  Mimas     - Herschel crater (~130 km), warm thermal anomaly
  Tethys    - Odysseus crater + Ithaca Chasma (~2000 km rift)
  Dione     - bright tectonic "wispy" terrain
  Rhea      - heavily cratered ice
  Iapetus   - Cassini Regio dark leading side + equatorial ridge
  Hyperion  - irregular, spongy/porous surface
  Titan     - global orange haze, detached layer, polar hood
"""
import math
import random
import sys

sys.path.insert(0, "/tmp/opencode")
from ascii_arcade_wallpaper import W, H, fill_rect, draw_text, write_png  # noqa: E402
from enceladus_jupiter_simple import (  # noqa: E402
    interp, mix, blend_rect, band_color, scale, hash01, moon, plume,
)

OUT = "/home/anontokoy/Pictures/saturn-system-wide-2560x1600.png"
LIGHT = (-0.50, -0.28, 0.82)

ICE = [(16, 15, 14), (42, 40, 38), (82, 80, 76), (128, 125, 118),
       (178, 173, 162), (218, 211, 196), (246, 241, 228)]
IAP_DARK = [(6, 6, 6), (16, 14, 12), (30, 26, 22), (46, 40, 34),
            (66, 58, 48), (90, 80, 66)]
IAP_BRIGHT = [(26, 26, 28), (60, 62, 68), (112, 116, 124), (165, 169, 176),
              (212, 215, 218), (240, 240, 238)]
TITAN = [(30, 20, 10), (70, 45, 20), (120, 80, 38), (170, 120, 60),
         (205, 155, 85), (228, 185, 115), (242, 205, 140)]
HYP = [(20, 18, 16), (45, 40, 36), (80, 72, 64), (120, 108, 96),
       (160, 148, 134), (200, 188, 172), (228, 218, 204)]


def make_craters(seed, n, rmin, rmax, dmin, dmax):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a = rng.random() * 2 * math.pi
        rad = math.sqrt(rng.random()) * 0.85
        out.append((math.cos(a) * rad, math.sin(a) * rad,
                    rng.uniform(rmin, rmax), rng.uniform(dmin, dmax)))
    return out


CRATER_SETS = {
    'rhea': make_craters(1, 45, 0.05, 0.13, 0.03, 0.09),
    'mimas': make_craters(2, 16, 0.05, 0.10, 0.03, 0.06),
    'tethys': make_craters(3, 20, 0.05, 0.11, 0.03, 0.06),
    'dione': make_craters(4, 22, 0.05, 0.11, 0.03, 0.06),
    'iapetus': make_craters(5, 22, 0.05, 0.12, 0.03, 0.06),
    'hyperion': make_craters(6, 34, 0.06, 0.16, 0.06, 0.13),
    'tiny': make_craters(7, 6, 0.15, 0.30, 0.05, 0.10),
}


def body(fb, cx, cy, r, stops, kind):
    lx, ly, lz = LIGHT
    step = 4
    craters = CRATER_SETS.get(kind, ())
    xm = max(0, int(cx - r * 1.35))
    xM = min(W, int(cx + r * 1.35) + step)
    ym = max(0, int(cy - r * 1.35))
    yM = min(H, int(cy + r * 1.35) + step)
    for gy in range(ym, yM, step):
        for gx in range(xm, xM, step):
            px = gx + step / 2
            py = gy + step / 2
            ddx = px - cx
            ddy = py - cy
            warp = 1.0
            if kind == 'hyperion':
                a = math.atan2(ddy, ddx)
                warp = 1.0 + 0.13 * math.sin(3 * a + 1.0) + 0.08 * math.sin(5 * a + 2.0)
            rw = r * warp
            dx = ddx / rw
            dy = ddy / rw
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                if kind == 'titan' and d2 < 1.44:
                    d = math.sqrt(d2)
                    a = 0.10 * (1.0 - (d - 1.0) / 0.2)
                    if a > 0:
                        blend_rect(fb, gx, gy, step, step, (225, 165, 95), a)
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz)
            amb = 0.16 if kind == 'titan' else 0.09
            v = amb + (1.0 - amb) * v
            v += 0.012 * math.sin(dx * 17.0 + 1.3) * math.sin(dy * 19.0 - 0.7)
            for ccx, ccy, crad, cd in craters:
                c2 = ((dx - ccx) ** 2 + (dy - ccy) ** 2) / (crad * crad)
                if c2 < 1.0:
                    v -= cd * math.exp(-2.0 * c2)
            if kind == 'mimas':
                h2 = ((dx + 0.15) ** 2 + (dy + 0.08) ** 2) / (0.42 ** 2)
                if h2 < 1.0:
                    v -= 0.16 * math.exp(-1.6 * h2)
                    if h2 > 0.67:
                        v += 0.05
            elif kind == 'tethys':
                o2 = ((dx - 0.15) ** 2 + (dy + 0.05) ** 2) / (0.30 ** 2)
                if o2 < 1.0:
                    v -= 0.12 * math.exp(-1.6 * o2)
                yc = -0.55 * dx + 0.08 * math.sin(3.0 * dx)
                if abs(dy - yc) < 0.022 and abs(dx) < 0.8:
                    v -= 0.10
            elif kind == 'dione':
                for ox, oy, rr in ((0.35, -0.20, 0.78), (0.50, 0.10, 0.86),
                                   (0.18, -0.45, 0.56), (-0.05, -0.50, 0.60)):
                    dd = abs(math.hypot(dx - ox, dy - oy) - rr)
                    if dd < 0.012:
                        v += 0.12
            elif kind == 'iapetus':
                ridge = abs(dy - 0.05 * math.sin(dx * 2.5))
                if ridge < 0.03 and abs(dx) < 0.8:
                    v += 0.10
                v = min(1.0, max(0.0, v))
                t = dx * 0.9 + dy * 0.25
                w = min(1.0, max(0.0, (t + 0.15) / 0.30))
                col = mix(interp(IAP_DARK, v), interp(IAP_BRIGHT, v), w)
                if ridge < 0.03 and abs(dx) < 0.8:
                    col = mix(col, (220, 225, 230), 0.35)
                fill_rect(fb, gx, gy, step, step, col)
                continue
            elif kind == 'titan':
                if dy < -0.55:
                    v -= 0.05
            v = min(1.0, max(0.0, v))
            fill_rect(fb, gx, gy, step, step, interp(stops, v))


def jupiter(fb, cx, cy, r, tilt):
    lx, ly, lz = LIGHT
    ct, st = math.cos(tilt), math.sin(tilt)
    step = 4
    for gy in range(max(0, int(cy - r)), min(H, int(cy + r)) + step, step):
        for gx in range(max(0, int(cx - r)), min(W, int(cx + r)) + step, step):
            px = gx + step / 2
            py = gy + step / 2
            dx = (px - cx) / r
            dy = (py - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz) ** 1.15
            v = 0.12 + 0.88 * v
            by = dx * st + dy * ct
            warp = 0.010 * math.sin(dx * 7.0) + 0.006 * math.sin(dx * 17.0 + dy * 3.0)
            base = band_color(by + 0.5 + warp)
            f = (0.30 + 0.90 * v) * (0.96 + 0.06 * hash01(gx // step, gy // step))
            sdx = (px - (cx + 0.25 * r)) / (0.11 * r)
            sdy = (py - (cy + 0.30 * r)) / (0.055 * r)
            s2 = sdx * sdx + sdy * sdy
            if s2 < 1.0:
                base = mix(base, (246, 238, 224), 0.45 * (1.0 - s2))
                f *= 1.04
            fill_rect(fb, gx, gy, step, step, scale(base, f))


def tiny_moon(fb, cx, cy, r, stops):
    lx, ly, lz = LIGHT
    step = 3
    kind = 'tiny'
    for gy in range(int(cy - r) - step, int(cy + r) + step, step):
        for gx in range(int(cx - r) - step, int(cx + r) + step, step):
            px = gx + step / 2
            py = gy + step / 2
            dx = (px - cx) / r
            dy = (py - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz)
            for ccx, ccy, crad, cd in CRATER_SETS[kind]:
                c2 = ((dx - ccx) ** 2 + (dy - ccy) ** 2) / (crad * crad)
                if c2 < 1.0:
                    v -= cd * math.exp(-2.0 * c2)
            v = min(1.0, max(0.0, v))
            fill_rect(fb, gx, gy, step, step, interp(stops, v))


def main():
    fb = bytearray(W * H * 3)
    for y in range(H):
        t = y / H
        b = 5 + int(2 * t)
        fill_rect(fb, 0, y, W, 1, (b - 4, b - 3, b))

    rng = random.Random(21)
    for _ in range(1500):
        sx = rng.randrange(0, W - 4)
        sy = rng.randrange(0, H - 4)
        b = rng.choice([40, 60, 85, 120, 165, 215, 255])
        size = 2 if b < 90 else (3 if b < 180 else 4)
        tint = rng.choice([(0, 0, 14), (0, 4, 18), (0, 0, 0), (14, 6, -8)])
        fill_rect(fb, sx, sy, size, size,
                  (min(255, b + tint[0]), min(255, b + tint[1]),
                   min(255, b + tint[2])))

    for _ in range(2600):
        t = rng.random()
        x = int(t * W + rng.gauss(0, 70 + 50 * math.sin(t * math.pi)))
        y = int(1250 - t * 900 + rng.gauss(0, 90 + 70 * math.sin(t * math.pi)))
        b = rng.choice([22, 30, 40, 52, 66])
        fill_rect(fb, x, y, 2, 2, (b - 6, b - 2, min(255, b + 8)))
    for _ in range(700):
        t = rng.random()
        x = int(t * W + rng.gauss(0, 42))
        y = int(1250 - t * 900 + rng.gauss(0, 45))
        b = rng.choice([55, 70, 85, 100])
        fill_rect(fb, x, y, 2, 2, (b - 6, b - 2, min(255, b + 8)))

    for ncx, ncy, col in ((260, 820, (16, 40, 46)),
                          (2100, 1430, (20, 28, 50)),
                          (560, 320, (38, 26, 42))):
        for _ in range(300):
            rr = abs(rng.gauss(0, 60))
            aa = rng.random() * 2 * math.pi
            x = int(ncx + math.cos(aa) * rr)
            y = int(ncy + math.sin(aa) * rr * 0.6)
            b = rng.uniform(0.4, 1.0)
            fill_rect(fb, x, y, 3, 3,
                      (int(col[0] * b), int(col[1] * b), int(col[2] * b)))

    for gcx, gcy, ang in ((270, 540, 0.5), (2380, 150, -0.3),
                          (660, 1530, 0.2), (1600, 1450, 0.8)):
        ca, sa = math.cos(ang), math.sin(ang)
        for _ in range(26):
            ex = rng.gauss(0, 9)
            ey = rng.gauss(0, 3)
            x = int(gcx + ex * ca - ey * sa)
            y = int(gcy + ex * sa + ey * ca)
            b = rng.choice([70, 90, 115])
            fill_rect(fb, x, y, 2, 2, (b, b - 3, b + 4))

    for ddy in range(-34, 35):
        for ddx in range(-34, 35):
            dd = math.hypot(ddx, ddy)
            if dd <= 34:
                blend_rect(fb, 150 + ddx, 230 + ddy, 1, 1, (255, 246, 218),
                           0.30 * math.exp(-dd / 8.5))
    fill_rect(fb, 148, 228, 5, 5, (255, 252, 240))

    jupiter(fb, 2070, 400, 340, math.radians(-8))
    tiny_moon(fb, 1740, 190, 10, [(35, 28, 12), (90, 70, 30), (150, 120, 55),
                                  (200, 170, 85), (230, 205, 130)])
    tiny_moon(fb, 1650, 610, 9, [(30, 30, 32), (90, 92, 96), (150, 152, 156),
                                 (205, 206, 206), (238, 238, 236)])
    tiny_moon(fb, 2460, 320, 11, [(28, 24, 20), (70, 62, 52), (120, 108, 92),
                                  (168, 156, 138), (215, 205, 190)])
    tiny_moon(fb, 2500, 660, 12, [(16, 14, 12), (45, 40, 35), (78, 70, 60),
                                  (112, 102, 88), (150, 138, 122)])

    body(fb, 420, 1190, 140, TITAN, 'titan')
    body(fb, 2290, 960, 85, IAP_BRIGHT, 'iapetus')
    body(fb, 1870, 1170, 70, ICE, 'dione')
    body(fb, 1190, 1320, 88, ICE, 'rhea')
    body(fb, 1330, 340, 62, ICE, 'tethys')
    body(fb, 1560, 690, 58, ICE, 'mimas')
    body(fb, 980, 300, 45, HYP, 'hyperion')
    tiny_moon(fb, 620, 160, 12, [(18, 16, 14), (48, 44, 38), (85, 78, 68),
                                 (125, 115, 100), (165, 152, 135)])
    tiny_moon(fb, 2170, 245, 13, [(18, 16, 14), (48, 44, 38), (85, 78, 68),
                                  (125, 115, 100), (165, 152, 135)])

    moon(fb, 760, 700, 170, ambient=0.09)
    plume(fb, 760, 700, 170)

    lc = (125, 132, 142)
    draw_text(fb, "HYPERION", 1040, 290, 4, lc)
    draw_text(fb, "TETHYS", 1410, 330, 4, lc)
    draw_text(fb, "MIMAS", 1620, 600, 4, lc)
    draw_text(fb, "ENCELADUS", 930, 540, 4, (170, 178, 188))
    draw_text(fb, '-', 880, 552, 4, lc)
    draw_text(fb, "IAPETUS", 2230, 1070, 4, lc)
    draw_text(fb, "DIONE", 1810, 1260, 4, lc)
    draw_text(fb, "RHEA", 1130, 1430, 4, lc)
    draw_text(fb, "TITAN", 350, 1350, 4, lc)

    draw_text(fb, "SATURNIAN SYSTEM", 40, 1500, 4, (140, 146, 156))
    draw_text(fb, "CASSINI-DERIVED COMPOSITE / NOT TO SCALE", 40, 1540, 4,
              (90, 96, 106))

    dim = bytes(int(i * 0.95) for i in range(256))
    for y in range(2, H, 3):
        st = y * W * 3
        fb[st:st + W * 3] = fb[st:st + W * 3].translate(dim)

    write_png(OUT, fb)
    print("written", OUT, W, "x", H)


if __name__ == '__main__':
    main()
