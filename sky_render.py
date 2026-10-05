#!/usr/bin/env python3
"""Real-sky background renderer (galactic Lambert cylindrical equal-area).

Data: HYG v4.1 star catalog (Hipparcos/Yale/Gliese) and OpenNGC
(Messier/NGC/IC). Milky Way diffuse light and dust lanes are stylized
after COBE/DIRBE & Gaia sky maps.
"""
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))

from ascii_arcade_wallpaper import W, H, fill_rect, draw_text
from enceladus_jupiter_simple import blend_rect

D2R = math.pi / 180.0
AG = 192.85948 * D2R
DG = 27.12825 * D2R
L0 = 122.93192 * D2R
PX_ARCMIN = 7.111 / 60.0


def radec_to_gal(ra, dec):
    a = ra * D2R
    d = dec * D2R
    sb = math.sin(d) * math.sin(DG) + math.cos(d) * math.cos(DG) * math.cos(a - AG)
    sb = max(-1.0, min(1.0, sb))
    b = math.asin(sb)
    l = L0 - math.atan2(math.cos(d) * math.sin(a - AG),
                        math.sin(d) * math.cos(DG)
                        - math.cos(d) * math.sin(DG) * math.cos(a - AG))
    return math.degrees(l) % 360.0, math.degrees(b)


def gal_xy(l, b):
    return (((l + 180.0) % 360.0) / 360.0 * W,
            (1.0 - math.sin(b * D2R)) / 2.0 * H)


def tangents(ra, dec):
    x0, y0 = gal_xy(*radec_to_gal(ra, dec))
    x1, y1 = gal_xy(*radec_to_gal(ra + 0.02, dec))
    x2, y2 = gal_xy(*radec_to_gal(ra, dec + 0.02))
    ex, ey = x1 - x0, y1 - y0
    nx, ny = x2 - x0, y2 - y0
    e = math.hypot(ex, ey) or 1.0
    n = math.hypot(nx, ny) or 1.0
    return (ex / e, ey / e), (nx / n, ny / n)


def draw_milky_way(fb):
    step = 4
    for gy in range(0, H, step):
        py = gy + step / 2.0
        b = math.degrees(math.asin(1.0 - 2.0 * py / H))
        for gx in range(0, W, step):
            px = gx + step / 2.0
            l = (px / W * 360.0 - 180.0) % 360.0
            dl = ((l + 180.0) % 360.0) - 180.0
            env = (0.20 + 0.80 * math.exp(-(dl / 55.0) ** 2)
                   + 0.30 * math.exp(-((dl - 80.0) / 22.0) ** 2)
                   + 0.25 * math.exp(-((dl + 70.0) / 18.0) ** 2))
            sig = 5.5 + 3.5 * math.exp(-(dl / 60.0) ** 2)
            val = env * math.exp(-(b / sig) ** 2)
            val += 0.22 * env * math.exp(-(b / (sig * 2.2)) ** 2)
            val += 0.45 * math.exp(-((dl / 9.0) ** 2 + (b / 5.0) ** 2))
            if -80.0 <= dl <= 110.0:
                br = -0.8 * math.sin(math.pi * (dl + 80.0) / 190.0)
                w_in = min(1.0, (dl + 80.0) / 18.0)
                w_out = min(1.0, (110.0 - dl) / 18.0)
                win = 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(w_in, w_out)))
                val *= 1.0 - 0.38 * win * math.exp(-((b - br) / 0.85) ** 2)
            val *= 1.0 - 0.70 * math.exp(-(((dl + 57.0) / 6.0) ** 2
                                           + ((b + 1.0) / 3.0) ** 2))
            if val <= 0.0:
                continue
            val = min(1.0, val)
            warm = min(1.0, env)
            nz = 0.80 + 0.40 * ((((gx // step) * 73856093)
                                 ^ ((gy // step) * 19349663)) & 255) / 255.0
            f = val * 0.70 * nz
            T = 0.035
            if f < T:
                d = ((((gx // step) * 83492791)
                      ^ ((gy // step) * 29874019)) & 255) / 255.0
                if d > f / T:
                    continue
                f = T
            fill_rect(fb, gx, gy, step, step,
                      (int((150 + 60 * warm) * f + 0.5),
                       int((145 + 55 * warm) * f + 0.5),
                       int((160 + 25 * warm) * f + 0.5)))


def star_rgb(bv):
    if bv < -0.2:
        return (155, 176, 255)
    if bv < 0.0:
        return (170, 191, 255)
    if bv < 0.3:
        return (202, 215, 255)
    if bv < 0.6:
        return (248, 247, 255)
    if bv < 0.9:
        return (255, 244, 232)
    if bv < 1.2:
        return (255, 219, 186)
    if bv < 1.5:
        return (255, 199, 155)
    return (255, 190, 140)


def draw_star(fb, x, y, r, color, a):
    x0, y0 = int(x - r) - 1, int(y - r) - 1
    x1, y1 = int(x + r) + 2, int(y + r) + 2
    for yy in range(max(0, y0), min(H, y1)):
        for xx in range(max(0, x0), min(W, x1)):
            dd = math.hypot(xx + 0.5 - x, yy + 0.5 - y)
            if dd > r:
                continue
            aa = a if dd < r - 0.9 else a * 0.55
            blend_rect(fb, xx, yy, 1, 1, color, aa)


def draw_stars(fb):
    with open(os.path.join(BASE, "sky_stars.txt")) as f:
        for line in f:
            ra, dec, mag, ci = (float(v) for v in line.split())
            l, b = radec_to_gal(ra, dec)
            x, y = gal_xy(l, b)
            if not (-6 <= x <= W + 6 and -6 <= y <= H + 6):
                continue
            color = star_rgb(ci)
            a = max(0.18, min(1.0, 0.38 + (7.5 - mag) * 0.11))
            r = max(0.7, min(3.4, 0.9 + 2.3 * math.exp(-0.42 * mag)))
            if mag < 2.6:
                draw_star(fb, x, y, r * 2.4, color, 0.16)
            draw_star(fb, x, y, r, color, a)


def draw_object(fb, name, otype, ra, dec, maj, minax, pa, label):
    l, b = radec_to_gal(ra, dec)
    x, y = gal_xy(l, b)
    if not (-80 <= x <= W + 80 and -80 <= y <= H + 80):
        return
    scale = PX_ARCMIN
    amaj = max(1.5, maj * scale)
    amin = max(1.0, (minax or maj) * scale)
    (ex, ey), (nx, ny) = tangents(ra, dec)
    pr = pa * D2R
    vx = math.cos(pr) * nx + math.sin(pr) * ex
    vy = math.cos(pr) * ny + math.sin(pr) * ey
    ang = math.atan2(vy, vx)
    ca, sa = math.cos(ang), math.sin(ang)
    seed = (sum(ord(c) for c in name) % 977) / 977.0
    if otype in ("G", "GPair", "GTrpl", "GGroup"):
        rad = max(amaj, amin)
        big = name in ("LMC", "SMC")
        for yy in range(int(y - rad) - 1, int(y + rad) + 2):
            for xx in range(int(x - rad) - 1, int(x + rad) + 2):
                if not (0 <= xx < W and 0 <= yy < H):
                    continue
                ux, uy = xx + 0.5 - x, yy + 0.5 - y
                u = ux * ca + uy * sa
                v = -ux * sa + uy * ca
                q = (u / amaj) ** 2 + (v / amin) ** 2
                if q > 1.0:
                    continue
                a = 0.16 * math.exp(-1.4 * q) + 0.20 * math.exp(-9.0 * q)
                if big:
                    irr = (0.72
                           + 0.20 * math.sin(u * 0.055 + seed * 7.0)
                           * math.sin(v * 0.071 - seed * 3.0)
                           + 0.10 * math.sin(u * 0.13 - v * 0.09 + seed * 11.0)
                           + 0.06 * math.sin(u * 0.31 + v * 0.23 + seed * 5.0))
                    a = (0.26 * math.exp(-1.2 * q) + 0.22 * math.exp(-8.0 * q)) * irr
                    if name == "LMC":
                        bar = math.exp(-(v / (amin * 0.30)) ** 2) \
                            * math.exp(-(u / (amaj * 0.85)) ** 2)
                        a += 0.18 * bar
                a = min(0.45, a)
                blend_rect(fb, xx, yy, 1, 1, (208, 198, 182), a)
    elif otype == "GCl":
        rad = max(2.0, amaj)
        for yy in range(int(y - rad) - 1, int(y + rad) + 2):
            for xx in range(int(x - rad) - 1, int(x + rad) + 2):
                if not (0 <= xx < W and 0 <= yy < H):
                    continue
                q = ((xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2) / (rad * rad)
                if q > 1.0:
                    continue
                blend_rect(fb, xx, yy, 1, 1, (240, 232, 210),
                           0.10 + 0.35 * math.exp(-4.0 * q))
    elif otype == "OCl":
        rad = max(2.5, amaj * 0.8)
        n = int(5 + 10 * min(1.0, maj / 60.0))
        for k in range(n):
            aa = seed * 6.28 + k * 2.399
            rr = rad * math.sqrt((k + 0.6) / n)
            sx = x + math.cos(aa) * rr
            sy = y + math.sin(aa) * rr * 0.7
            draw_star(fb, sx, sy, 1.0, (230, 235, 245), 0.30)
        blend_rect(fb, int(x - rad), int(y - rad), int(2 * rad), int(2 * rad),
                   (120, 130, 150), 0.05)
    else:
        if otype == "PN":
            col = (130, 235, 220)
        elif otype == "SNR":
            col = (250, 110, 90)
        elif otype in ("RfN", "EmN"):
            col = (130, 165, 245)
        else:
            col = (250, 130, 165)
        rad = max(2.5, amaj)
        for yy in range(int(y - rad) - 1, int(y + rad) + 2):
            for xx in range(int(x - rad) - 1, int(x + rad) + 2):
                if not (0 <= xx < W and 0 <= yy < H):
                    continue
                ux, uy = xx + 0.5 - x, yy + 0.5 - y
                q = math.hypot(ux, uy) / rad
                if q > 1.0:
                    continue
                n = (math.sin(ux * 0.55 + seed * 9.0) * math.sin(uy * 0.47 - seed * 5.0)
                     + 0.6 * math.sin(ux * 0.9 - uy * 1.1 + seed * 13.0))
                mask = 0.5 + 0.35 * n
                if otype == "PN":
                    mask *= 0.4 + math.exp(-((q - 0.62) / 0.25) ** 2)
                else:
                    mask *= 1.0 - q * q
                a = 0.22 * max(0.0, mask)
                blend_rect(fb, xx, yy, 1, 1, col, a)
    if label:
        place_label(fb, label, x, y, amaj)


PLACED_LABELS = []
PENDING_LABELS = []
RESERVED = []
OBSTRUCT = None


def place_label(fb, txt, x, y, amaj):
    w = len(txt) * 12 + 4
    h = 16
    cands = [
        (int(x + amaj * 0.6 + 6), int(y - 12)),
        (int(x - amaj * 0.6 - 6 - w), int(y - 12)),
        (int(x + amaj * 0.6 + 6), int(y + 6)),
        (int(x - amaj * 0.6 - 6 - w), int(y + 6)),
        (int(x - w / 2), int(y - amaj - 22)),
        (int(x - w / 2), int(y + amaj + 8)),
        (int(x - w / 2), int(y - amaj - 40)),
    ]
    for cx, cy in cands:
        if cx < 4 or cx + w > W - 4 or cy < 4 or cy + h > H - 4:
            continue
        clash = False
        for px, py, pw, ph in PLACED_LABELS:
            if cx < px + pw + 5 and px < cx + w + 5 \
                    and cy < py + ph + 3 and py < cy + h + 3:
                clash = True
                break
        if not clash:
            for rx0, ry0, rx1, ry1 in RESERVED:
                if cx < rx1 and rx0 < cx + w and cy < ry1 and ry0 < cy + h:
                    clash = True
                    break
        if not clash and OBSTRUCT is not None:
            for gy in range(5):
                for gx in range(5):
                    sx = cx + w * gx / 4.0
                    sy = cy + h * gy / 4.0
                    if OBSTRUCT(sx, sy):
                        clash = True
                        break
                if clash:
                    break
        if clash:
            continue
        PENDING_LABELS.append((txt, cx, cy))
        PLACED_LABELS.append((cx, cy, w, h))
        return


def draw_pending_labels(fb):
    for txt, cx, cy in PENDING_LABELS:
        draw_text(fb, txt, cx, cy, 2, (108, 116, 128))


def draw_deep_sky(fb):
    with open(os.path.join(BASE, "sky_objects.txt")) as f:
        for line in f:
            name, otype, ra, dec, maj, minax, pa, label = line.rstrip("\n").split("|")
            draw_object(fb, name, otype, float(ra), float(dec), float(maj),
                        float(minax), float(pa), label)


def draw_real_sky(fb):
    PLACED_LABELS.clear()
    PENDING_LABELS.clear()
    draw_milky_way(fb)
    draw_stars(fb)
    draw_deep_sky(fb)
