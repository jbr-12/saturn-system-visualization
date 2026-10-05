#!/usr/bin/env python3
"""Crop + upscale a region of our filter-0 RGB PNG for visual verification."""
import struct
import sys
import zlib

SRC = sys.argv[1]
X0, Y0, X1, Y1 = map(int, sys.argv[2:6])
SCALE = int(sys.argv[6]) if len(sys.argv) > 6 else 2
OUT = sys.argv[7] if len(sys.argv) > 7 else "/tmp/opencode/crop.png"

with open(SRC, "rb") as f:
    data = f.read()
assert data[:8] == b"\x89PNG\r\n\x1a\n"
pos = 8
w = h = None
idat = b""
while pos < len(data):
    ln = struct.unpack(">I", data[pos:pos + 4])[0]
    tag = data[pos + 4:pos + 8]
    chunk = data[pos + 8:pos + 8 + ln]
    if tag == b"IHDR":
        w, h = struct.unpack(">II", chunk[:8])
    elif tag == b"IDAT":
        idat += chunk
    pos += 12 + ln
raw = zlib.decompress(idat)
stride = w * 3 + 1
cw, ch = X1 - X0, Y1 - Y0
canvas = bytearray(cw * SCALE * ch * SCALE * 3)
for y in range(ch):
    row = raw[(Y0 + y) * stride + 1:(Y0 + y) * stride + 1 + w * 3]
    for x in range(cw):
        r, g, b = row[(X0 + x) * 3:(X0 + x) * 3 + 3]
        for sy in range(SCALE):
            base = ((y * SCALE + sy) * cw * SCALE + x * SCALE) * 3
            for sx in range(SCALE):
                i = base + sx * 3
                canvas[i] = r
                canvas[i + 1] = g
                canvas[i + 2] = b
ow, oh = cw * SCALE, ch * SCALE
raw_out = bytearray()
for y in range(oh):
    raw_out.append(0)
    raw_out += canvas[y * ow * 3:(y + 1) * ow * 3]


def chunk(tag, payload):
    return (struct.pack(">I", len(payload)) + tag + payload +
            struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff))


with open(OUT, "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n")
    f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", ow, oh, 8, 2, 0, 0, 0)))
    f.write(chunk(b"IDAT", zlib.compress(bytes(raw_out), 6)))
    f.write(chunk(b"IEND", b""))
print("wrote", OUT, ow, "x", oh)
