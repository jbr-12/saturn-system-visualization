#!/usr/bin/env python3
"""Saturnian system, true-scale bodies, annotated name plates.

Saturn + 8 moons drawn at true relative radii (mean radii, IAU/Cassini).
Orbital distances remain compressed (stated). Jupiter removed.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ascii_arcade_wallpaper import W, H, fill_rect, draw_text, write_png  # noqa: E402
from enceladus_jupiter_simple import interp, mix, blend_rect  # noqa: E402
from saturn_system_wide import TITAN, IAP_DARK, IAP_BRIGHT, HYP  # noqa: E402
from sky_render import draw_real_sky  # noqa: E402

OUT = "/home/anontokoy/Pictures/saturn-true-scale-2560x1600.png"
SCX, SCY = 1280, 860
TILT = math.radians(-10)
CT, ST = math.cos(TILT), math.sin(TILT)
SQ = 0.42
SAT_R = 270.0
SAT_MEAN_KM = 58232.0
FLAT = 0.902
SCALE = SAT_R / SAT_MEAN_KM
LIGHT = (-0.50, -0.28, 0.82)

ICE = [(16, 15, 14), (42, 40, 38), (82, 80, 76), (128, 125, 118),
       (178, 173, 162), (218, 211, 196), (246, 241, 228)]

MOONS = [
    ("MIMAS", 690.0, 3.60, 198.2, "mimas"),
    ("ENCELADUS", 740.0, 1.62, 252.1, "enceladus"),
    ("TETHYS", 785.0, 5.90, 531.1, "ice"),
    ("DIONE", 845.0, 0.75, 561.4, "ice"),
    ("RHEA", 935.0, 2.50, 763.8, "ice"),
    ("TITAN", 1130.0, 0.10, 2574.7, "titan"),
    ("HYPERION", 1200.0, 5.40, 135.0, "hyperion"),
    ("IAPETUS", 1650.0, 4.10, 734.5, "iapetus"),
]

PLATE_POS = {
    "IAPETUS": (430, 390), "MIMAS": (300, 940), "RHEA": (700, 1340),
    "ENCELADUS": (1150, 1340), "TITAN": (2150, 560), "DIONE": (2120, 1020),
    "TETHYS": (2140, 430), "HYPERION": (1780, 230),
}
PLATE_SUB = {
    "MIMAS": "R 198 KM", "ENCELADUS": "R 252 KM / H2O", "TETHYS": "R 531 KM",
    "DIONE": "R 561 KM", "RHEA": "R 764 KM", "TITAN": "R 2575 KM",
    "HYPERION": "R 135 KM", "IAPETUS": "R 735 KM",
}


def orbit_pt(a, t):
    ex = a * math.cos(t)
    ey = a * SQ * math.sin(t)
    return (SCX + ex * CT - ey * ST, SCY + ex * ST + ey * CT, ey)


MOON_INFO = {}
for name, a, t, rkm, kind in MOONS:
    x, y, ey = orbit_pt(a, t)
    MOON_INFO[name] = (x, y, ey, max(2.2, rkm * SCALE), kind)


def draw_orbits(fb):
    for name, a, t_phase, rkm, kind in MOONS:
        dt = 6.0 / a
        t = 0.0
        while t < 2 * math.pi:
            x, y, _ = orbit_pt(a, t)
            fill_rect(fb, int(x), int(y), 2, 2, (48, 54, 64))
            t += dt


def dot_body(fb, cx, cy, r, kind):
    lx, ly, lz = LIGHT
    rr = max(r, 2.2)
    for gy in range(int(cy - rr) - 1, int(cy + rr) + 2):
        for gx in range(int(cx - rr) - 1, int(cx + rr) + 2):
            px = gx + 0.5
            py = gy + 0.5
            dx = (px - cx) / rr
            dy = (py - cy) / rr
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                if kind == 'titan' and d2 < 1.6:
                    d = math.sqrt(d2)
                    a = 0.10 * (1.0 - (d - 1.0) / 0.6)
                    if a > 0:
                        blend_rect(fb, gx, gy, 1, 1, (225, 170, 100), a)
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz)
            v = 0.12 + 0.88 * v
            if kind == 'titan':
                base = interp(TITAN, min(1.0, max(0.0, 0.5 + 0.35 * dy)))
                f = 0.55 + 0.55 * v
                col = (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
                       min(255, int(base[2] * f)))
            elif kind == 'iapetus':
                w = min(1.0, max(0.0, dx * 1.2 + 0.35))
                col = mix(interp(IAP_DARK, v), interp(IAP_BRIGHT, v), w)
            elif kind == 'hyperion':
                col = interp(HYP, min(1.0, max(0.0, v * 0.9
                                      + 0.1 * math.sin(dx * 9) * math.sin(dy * 9))))
            else:
                col = interp(ICE, min(1.0, max(0.0, v * 0.92
                                      + 0.08 * math.sin(dx * 9) * math.sin(dy * 9))))
            fill_rect(fb, gx, gy, 1, 1, col)


def draw_rings(fb, near):
    base = (176, 160, 138)
    span = 680
    R2 = SAT_R * SAT_R
    zones = [(2.40, 2.42, 0.75), (2.305, 2.315, 0.04), (2.10, 2.35, 0.55),
             (2.02, 2.10, 0.07), (1.58, 2.02, 0.80), (1.28, 1.58, 0.30),
             (1.15, 1.28, 0.12)]
    for gy in range(max(0, SCY - span), min(H, SCY + span)):
        for gx in range(max(0, SCX - span), min(W, SCX + span)):
            relx, rely = gx + 0.5 - SCX, gy + 0.5 - SCY
            ex = relx * CT + rely * ST
            ey = -relx * ST + rely * CT
            if (ey > 0) != near:
                continue
            n2 = ex * ex + (ey / SQ) ** 2
            f = 0.0
            for lo, hi, zf in zones:
                if lo * lo * R2 <= n2 < hi * hi * R2:
                    f = zf
                    break
            if f <= 0:
                continue
            nz = 0.95 + 0.10 * (((gx * 2654435761) ^ (gy * 40503)) & 255) / 255.0
            i = (gy * W + gx) * 3
            fb[i] = int(base[0] * f * nz)
            fb[i + 1] = int(base[1] * f * nz)
            fb[i + 2] = int(base[2] * f * nz)


SAT_STOPS = [
    (150, 152, 158), (168, 164, 158), (192, 182, 164), (210, 190, 162),
    (220, 198, 164), (206, 174, 128), (230, 204, 164), (240, 222, 188),
    (244, 228, 196), (240, 224, 190), (216, 188, 146), (236, 214, 178),
    (222, 196, 160), (196, 184, 168), (176, 174, 170), (160, 160, 164),
    (148, 150, 158),
]
BELT_TINT = (204, 158, 108)
VIEW_TILT = math.acos(SQ)          # axis angle vs. line of sight (ring flatness)
V_SA = math.sin(VIEW_TILT)
V_CA = math.cos(VIEW_TILT)


def saturn(fb):
    lx, ly, lz = LIGHT
    step = 2
    for gy in range(int(SCY - SAT_R) - step, int(SCY + SAT_R) + step, step):
        for gx in range(int(SCX - SAT_R) - step, int(SCX + SAT_R) + step, step):
            px = gx + step / 2
            py = gy + step / 2
            relx, rely = px - SCX, py - SCY
            ex = relx * CT + rely * ST
            ey = -relx * ST + rely * CT
            dx = ex / SAT_R
            dy = ey / (SAT_R * FLAT)
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            nz = math.sqrt(1.0 - d2)
            v = max(0.0, dx * lx + dy * ly + nz * lz)
            sinphi = -V_SA * (ey / SAT_R) + V_CA * nz
            sinphi = max(-1.0, min(1.0, sinphi))
            frac = 0.5 + math.asin(sinphi) / math.pi
            u = dx
            fine = (math.sin(frac * 70.0 + 0.3)
                    + 0.55 * math.sin(frac * 150.0 + 2.0))
            jitter = 0.12 * math.sin(u * 6.0 + 2.0) * math.sin(frac * 30.0)
            taper = 0.35 + 0.65 * math.sin(math.pi * frac)
            base = interp(SAT_STOPS, frac)
            t = max(0.0, -(fine + jitter)) * taper
            r = base[0] + (BELT_TINT[0] - base[0]) * 0.22 * t
            g = base[1] + (BELT_TINT[1] - base[1]) * 0.22 * t
            b = base[2] + (BELT_TINT[2] - base[2]) * 0.22 * t
            lum = 1.0 + 0.045 * (fine + jitter) * taper
            lum *= 1.0 + 0.012 * math.sin(u * 9.0 + frac * 6.0)
            shadow = 1.0 - 0.38 * math.exp(-((sinphi + 0.10) / 0.05) ** 2)
            shade = 0.34 + 0.78 * v
            limbdark = 0.55 + 0.45 * nz
            f = lum * shade * limbdark * shadow
            fill_rect(fb, gx, gy, step, step,
                      (min(255, int(r * f)),
                       min(255, int(g * f)),
                       min(255, int(b * f))))
            if d2 <= 1.05 and gx + step <= W and gy + step <= H:
                for yy in range(gy, gy + step):
                    for xx in range(gx, gx + step):
                        rx = xx + 0.5 - SCX
                        ry = yy + 0.5 - SCY
                        e2x = rx * CT + ry * ST
                        e2y = -rx * ST + ry * CT
                        q = (e2x / SAT_R) ** 2 + (e2y / (SAT_R * FLAT)) ** 2
                        if 1.0 < q <= 1.05:
                            a = 0.30 * (1.0 - (q - 1.0) / 0.05) \
                                * max(0.25, min(1.0, 0.35 + v))
                            blend_rect(fb, xx, yy, 1, 1, (205, 195, 178), a)


def plate(fb, title, sub, x, y, tx, ty, marker_r):
    w = max(len(title) * 18, len(sub) * 12) + 18
    h = 48
    blend_rect(fb, x, y, w, h, (3, 5, 8), 0.62)
    edge = (62, 70, 84)
    fill_rect(fb, x, y, w, 1, edge)
    fill_rect(fb, x, y + h - 1, w, 1, edge)
    fill_rect(fb, x, y, 1, h, edge)
    fill_rect(fb, x + w - 1, y, 1, h, edge)
    draw_text(fb, title, x + 9, y + 5, 3, (200, 206, 214))
    draw_text(fb, sub, x + 9, y + 30, 2, (118, 126, 140))
    ccx, ccy = x + w / 2, y + h / 2
    dx, dy = tx - ccx, ty - ccy
    if abs(dx) / (w / 2) > abs(dy) / (h / 2):
        t = (w / 2) / abs(dx)
    else:
        t = (h / 2) / abs(dy)
    sx, sy = ccx + dx * t, ccy + dy * t
    dirx, diry = tx - sx, ty - sy
    L = math.hypot(dirx, diry)
    stop = L - ((marker_r + 8) if marker_r else 8)
    d = 7.0
    while d < stop:
        px = sx + dirx * d / L
        py = sy + diry * d / L
        fill_rect(fb, int(px), int(py), 2, 2, (96, 106, 120))
        d += 7.0
    if marker_r:
        for k in range(28):
            aa = k * 2 * math.pi / 28
            fill_rect(fb, int(tx + marker_r * math.cos(aa)),
                      int(ty + marker_r * math.sin(aa)), 1, 1, (118, 128, 142))


def main():
    fb = bytearray(W * H * 3)
    for y in range(H):
        t = y / H
        b = 5 + int(2 * t)
        fill_rect(fb, 0, y, W, 1, (b - 4, b - 3, b))

    import sky_render
    sky_render.RESERVED[:] = []
    for nm in MOON_INFO:
        px, py = PLATE_POS[nm]
        pw = max(len(nm) * 18, len(PLATE_SUB[nm]) * 12) + 18
        sky_render.RESERVED.append((px - 10, py - 12, px + pw + 10,
                                    py + 48 + 10))
    for t_, s_, px, py in (("SATURN", "R 58232 KM", 1600, 1210),
                           ("RING SYSTEM", "1.28-2.42 R_S", 320, 640)):
        pw = max(len(t_) * 18, len(s_) * 12) + 18
        sky_render.RESERVED.append((px - 10, py - 12, px + pw + 10,
                                    py + 48 + 10))

    def sky_obstructed(x, y):
        relx, rely = x - SCX, y - SCY
        ex = relx * CT + rely * ST
        ey = -relx * ST + rely * CT
        n2 = ex * ex + (ey / SQ) ** 2
        r2 = SAT_R * SAT_R
        if 1.15 * 1.15 * r2 <= n2 <= 2.42 * 2.42 * r2:
            return True
        dx = ex / SAT_R
        dy = ey / (SAT_R * FLAT)
        return dx * dx + dy * dy <= 1.0

    sky_render.OBSTRUCT = sky_obstructed

    draw_real_sky(fb)

    for ddy in range(-34, 35):
        for ddx in range(-34, 35):
            dd = math.hypot(ddx, ddy)
            if dd <= 34:
                blend_rect(fb, 150 + ddx, 230 + ddy, 1, 1, (255, 246, 218),
                           0.30 * math.exp(-dd / 8.5))
    fill_rect(fb, 148, 228, 5, 5, (255, 252, 240))

    draw_orbits(fb)
    sky_render.draw_pending_labels(fb)

    order = sorted(MOON_INFO, key=lambda n: (MOON_INFO[n][2] > 0,
                                             MOON_INFO[n][2]))
    back = [n for n in order if MOON_INFO[n][2] <= 0]
    front = [n for n in order if MOON_INFO[n][2] > 0]
    for name in back:
        x, y, _, r, kind = MOON_INFO[name]
        dot_body(fb, x, y, r, kind)

    draw_rings(fb, near=False)
    saturn(fb)
    draw_rings(fb, near=True)

    for name in front:
        x, y, _, r, kind = MOON_INFO[name]
        dot_body(fb, x, y, r, kind)

    for name in MOON_INFO:
        px, py = PLATE_POS[name]
        x, y, _, r, kind = MOON_INFO[name]
        plate(fb, name, PLATE_SUB[name], px, py, x, y, max(7, int(r) + 4))

    plate(fb, "SATURN", "R 58232 KM", 1600, 1210, 1450, 1060, 0)
    plate(fb, "RING SYSTEM", "1.28-2.42 R_S", 320, 640, 785, 748, 0)

    bar = int(20000 * SCALE)
    bx, by = 2470 - bar, 1470
    fill_rect(fb, bx, by, bar, 3, (150, 158, 170))
    fill_rect(fb, bx, by - 6, 3, 15, (150, 158, 170))
    fill_rect(fb, bx + bar - 3, by - 6, 3, 15, (150, 158, 170))
    draw_text(fb, "20 000 KM", bx, by - 34, 2, (150, 158, 170))

    draw_text(fb, "SATURNIAN SYSTEM", 40, 1500, 4, (140, 146, 156))
    draw_text(fb, "BODY SIZES TRUE SCALE / ORBITAL DISTANCES COMPRESSED",
              40, 1540, 4, (90, 96, 106))

    dim = bytes(int(i * 0.95) for i in range(256))
    for y in range(2, H, 3):
        st = y * W * 3
        fb[st:st + W * 3] = fb[st:st + W * 3].translate(dim)

    write_png(OUT, fb)
    print("written", OUT, W, "x", H)


if __name__ == '__main__':
    main()
