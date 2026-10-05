#!/usr/bin/env python3
"""Extract real-sky data from HYG v4.1 (Hipparcos/Yale/Gliese) and OpenNGC."""
import csv
import os

BASE = os.path.dirname(os.path.abspath(__file__))

STAR_OUT = os.path.join(BASE, "sky_stars.txt")
OBJ_OUT = os.path.join(BASE, "sky_objects.txt")
MAG_LIMIT = 7.5

stars = 0
with open(os.path.join(BASE, "hygdata_v41.csv"), newline="") as f, \
        open(STAR_OUT, "w") as out:
    for row in csv.DictReader(f):
        if row["id"] == "0":
            continue
        try:
            mag = float(row["mag"])
        except (ValueError, TypeError):
            continue
        if mag > MAG_LIMIT:
            continue
        ra = float(row["ra"]) * 15.0
        dec = float(row["dec"])
        try:
            ci = float(row["ci"])
        except (ValueError, TypeError):
            ci = 0.55
        out.write(f"{ra:.4f} {dec:.4f} {mag:.2f} {ci:.2f}\n")
        stars += 1
print("stars written:", stars)

EXTRA = {
    "NGC0869", "NGC0884", "NGC7000", "IC0434", "NGC2237", "NGC7293",
    "NGC5139", "NGC3372", "NGC0104", "NGC6960", "NGC6992", "NGC6888",
    "IC1396", "NGC7635", "NGC1499", "NGC281", "IC1805", "IC1848",
    "NGC2024", "NGC2264", "NGC6357", "NGC6334", "NGC5128", "NGC0253",
    "NGC2903", "NGC4565", "NGC6822", "NGC0598",
}
LABELS = {
    "NGC0224": "M31 ANDROMEDA", "NGC0598": "M33", "NGC5194": "M51",
    "NGC3031": "M81", "NGC3034": "M82", "NGC4594": "M104",
    "NGC5457": "M101", "NGC0253": "NGC 253", "NGC5128": "CENTAURUS A",
    "NGC4565": "NGC 4565", "NGC6822": "BARNARD",
    "NGC1976": "M42 ORION", "NGC1432": "M45 PLEIADES", "NGC6523": "M8",
    "NGC6611": "M16", "NGC6618": "M17", "NGC6656": "M22",
    "NGC6205": "M13", "NGC5272": "M3", "NGC7078": "M15",
    "NGC104": "47 TUC", "NGC5139": "OMEGA CEN", "NGC2632": "M44",
    "NGC2287": "M41", "NGC2168": "M35", "NGC6475": "M7", "NGC6405": "M6",
    "NGC2244": "ROSETTE", "NGC3372": "CARINA NEB", "NGC7000": "N. AMERICA",
    "NGC6960": "VEIL", "NGC6992": "VEIL E", "NGC6888": "CRESCENT",
    "IC1396": "IC 1396", "NGC7635": "BUBBLE", "NGC1499": "CALIFORNIA",
    "NGC281": "PACMAN", "IC1805": "HEART", "IC1848": "SOUL",
    "NGC2024": "HORSEHEAD", "NGC2264": "CONE", "NGC6357": "LOBSTER",
    "NGC6334": "CAT PAW", "NGC7293": "HELIX", "NGC6720": "M57 RING",
    "NGC6853": "M27 DUMBBELL", "NGC1952": "M1 CRAB", "NGC0869": "DOUBLE CL",
    "NGC0104": "47 TUC", "NGC0055": "NGC 55",
    "NGC0300": "NGC 300",
}
rows_out = 0
with open(os.path.join(BASE, "NGC.csv"), newline="") as f, open(OBJ_OUT, "w") as out:
    rd = csv.reader(f, delimiter=";")
    header = next(rd)
    idx = {name: i for i, name in enumerate(header)}
    for row in rd:
        if len(row) < len(header):
            continue
        name = row[idx["Name"]].strip()
        mnum = row[idx["M"]].strip()
        if not (mnum or name in EXTRA):
            continue
        ra_s = row[idx["RA"]].strip()
        dec_s = row[idx["Dec"]].strip()
        if not ra_s or not dec_s:
            continue
        hh, mm, ss = ra_s.split(":")
        ra = (float(hh) + float(mm) / 60 + float(ss) / 3600) * 15.0
        sign = -1.0 if dec_s[0] == "-" else 1.0
        dd, dm, ds = dec_s[1:].split(":")
        dec = sign * (float(dd) + float(dm) / 60 + float(ds) / 3600)
        try:
            maj = float(row[idx["MajAx"]])
        except (ValueError, TypeError):
            maj = 0.0
        try:
            minax = float(row[idx["MinAx"]])
        except (ValueError, TypeError):
            minax = 0.0
        try:
            pa = float(row[idx["PosAng"]])
        except (ValueError, TypeError):
            pa = 0.0
        otype = row[idx["Type"]].strip()
        label = LABELS.get(name, "")
        out.write(f"{name}|{otype}|{ra:.4f}|{dec:.4f}|{maj:.2f}|"
                  f"{minax:.2f}|{pa:.1f}|{label}\n")
        rows_out += 1
print("objects written:", rows_out)


LMC = "LMC|G|80.8942|-69.7561|645.0|550.0|113.0|LMC\n"
SMC = "SMC|G|13.1867|-72.8286|319.0|205.0|45.0|SMC\n"
with open(OBJ_OUT, "a") as out:
    out.write(LMC)
    out.write(SMC)
print("total objects:", rows_out + 2)
