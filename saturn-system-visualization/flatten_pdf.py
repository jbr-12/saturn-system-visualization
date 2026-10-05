#!/usr/bin/env python3
"""Flatten a PDF into one full-page image per page (pure python + pypdfium2).

Usage: python3 flatten_pdf.py SRC OUT [SCALE]
"""
import sys
import zlib

sys.path.insert(0, "/tmp/opencode/pylibs")
import pypdfium2 as pdfium  # noqa: E402

PAGE_W, PAGE_H = 595.276, 841.89


def add(objs, data):
    i = len(objs) + 1
    objs[i] = data
    return i


def main():
    src, outp = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 2.4
    pdf = pdfium.PdfDocument(src)
    n = len(pdf)
    objs = {1: (b"<< /Type /Catalog /Pages 2 0 R >>", None),
            2: (b"<< /Type /Pages /Count 0 /Kids [] >>", None)}
    kids = []
    for idx in range(n):
        bm = pdf[idx].render(scale=scale)
        w, h = bm.width, bm.height
        mv = bytes(memoryview(bm.buffer))
        rgb = bytearray(len(mv))
        rgb[0::3] = mv[2::3]
        rgb[1::3] = mv[1::3]
        rgb[2::3] = mv[0::3]
        comp = zlib.compress(bytes(rgb), 6)
        img = add(objs, (("<< /Type /XObject /Subtype /Image /Width %d "
                         "/Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 "
                         "/Filter /FlateDecode /Length %d >>"
                         % (w, h, len(comp))).encode("latin1"), comp))
        content = ("q %.3f 0 0 %.3f 0 0 cm /Im0 Do Q"
                   % (PAGE_W, PAGE_H)).encode("latin1")
        cid = add(objs, (b"<< >>", content))
        page = add(objs, (("<< /Type /Page /Parent 2 0 R "
                           "/MediaBox [0 0 %.3f %.3f] /Resources "
                           "<< /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>"
                           % (PAGE_W, PAGE_H, img, cid)).encode("latin1"), None))
        kids.append(page)
    pages = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (
        n, b" ".join(b"%d 0 R" % k for k in kids))
    cat = b"<< /Type /Catalog /Pages 2 0 R >>"
    title = b"\xfe\xff" + "土星系统 · 真实比例壁纸 — 图像说明".encode("utf-16-be")
    info = ("<< /Title <%s> /Author (anontokoy) /Creator "
            "(pure-python procedural renderer) >>"
            % title.hex().upper()).encode("latin1")
    objs[1] = (cat, None)
    objs[2] = (pages, None)
    info_id = add(objs, (info, None))

    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offs = {}
    for i in range(1, len(objs) + 1):
        offs[i] = len(out)
        d, stream = objs[i]
        out += b"%d 0 obj\n" % i
        if stream is None:
            out += d + b"\nendobj\n"
        else:
            out += d + b"\nstream\n" + stream + b"\nendstream\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for i in range(1, len(objs) + 1):
        out += b"%010d 00000 n \n" % offs[i]
    out += (b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\n"
            b"startxref\n%d\n%%%%EOF\n" % (len(objs) + 1, info_id, xref))
    with open(outp, "wb") as f:
        f.write(bytes(out))
    print("written", outp, n, "pages", len(out), "bytes")


if __name__ == "__main__":
    main()
