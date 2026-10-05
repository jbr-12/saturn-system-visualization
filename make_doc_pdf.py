#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a clean PDF document (Chinese) describing the Saturn wallpaper.

Pure Python: own PNG decoder, area-average downscaler, TTF parser and PDF
writer (Type0 / CIDFontType2 with embedded SimHei).  No third-party libs.
"""
import os
import struct
import sys
import zlib

BASE = os.path.dirname(os.path.abspath(__file__))

SRC = "/home/anontokoy/Pictures/saturn-true-scale-2560x1600.png"
OUT = "/home/anontokoy/Pictures/saturn-true-scale-说明.pdf"
FONT = "/mnt/c/Windows/Fonts/simhei.ttf"

PAGE_W = 595.276
PAGE_H = 841.89
ML = 56.0
MR = 56.0
MT = 62.0
MB = 52.0
CW = PAGE_W - ML - MR


# ---------------------------------------------------------------- PNG input
def read_png(path):
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", "not a png"
    pos = 8
    idat = b""
    W = H = 0
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        data = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            W, H, bd, ct = struct.unpack(">IIBB", data[:10])
            assert bd == 8 and ct == 2, "expect 8-bit rgb"
        elif tag == b"IDAT":
            idat += data
        pos += 12 + ln
    raw = zlib.decompress(idat)
    stride = W * 3
    px = bytearray(W * H * 3)
    for y in range(H):
        off = y * (stride + 1)
        assert raw[off] == 0
        px[y * stride:(y + 1) * stride] = raw[off + 1:off + 1 + stride]
    return W, H, px


def crop_rgb(px, W, H, x0, y0, x1, y1):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    w, h = x1 - x0, y1 - y0
    out = bytearray(w * h * 3)
    for y in range(h):
        s = ((y0 + y) * W + x0) * 3
        out[y * w * 3:(y + 1) * w * 3] = px[s:s + w * 3]
    return w, h, out


def downscale(px, W, H, ow, oh):
    out = bytearray(ow * oh * 3)
    xs = [(ox * W // ow, max(ox * W // ow + 1, (ox + 1) * W // ow))
          for ox in range(ow)]
    ys = [(oy * H // oh, max(oy * H // oh + 1, (oy + 1) * H // oh))
          for oy in range(oh)]
    for oy, (y0, y1) in enumerate(ys):
        row = oy * ow * 3
        for ox, (x0, x1) in enumerate(xs):
            r = g = b = 0
            n = (y1 - y0) * (x1 - x0)
            for yy in range(y0, y1):
                base = (yy * W + x0) * 3
                for i in range(base, base + (x1 - x0) * 3, 3):
                    r += px[i]
                    g += px[i + 1]
                    b += px[i + 2]
            j = row + ox * 3
            out[j] = r // n
            out[j + 1] = g // n
            out[j + 2] = b // n
    return out


# ---------------------------------------------------------------- TTF parse
class TTF:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.d = d
        n = struct.unpack(">H", d[4:6])[0]
        T = {}
        for i in range(n):
            o = 12 + 16 * i
            tag = d[o:o + 4].decode("latin1")
            off, ln = struct.unpack(">II", d[o + 8:o + 16])
            T[tag] = (off, ln)
        self.T = T
        ho = T["head"][0]
        self.upem = struct.unpack(">H", d[ho + 18:ho + 20])[0]
        self.xMin, self.yMin, self.xMax, self.yMax = struct.unpack(
            ">hhhh", d[ho + 36:ho + 44])
        hh = T["hhea"][0]
        self.ascent = struct.unpack(">h", d[hh + 4:hh + 6])[0]
        self.descent = struct.unpack(">h", d[hh + 6:hh + 8])[0]
        nh = struct.unpack(">H", d[hh + 34:hh + 36])[0]
        mx = T["maxp"][0]
        self.ng = struct.unpack(">H", d[mx + 4:mx + 6])[0]
        hm = T["hmtx"][0]
        self.adv = []
        for i in range(min(nh, self.ng)):
            self.adv.append(struct.unpack(">H", d[hm + 4 * i:hm + 4 * i + 2])[0])
        while len(self.adv) < self.ng:
            self.adv.append(self.adv[-1] if self.adv else 1000)
        self.cmap = {}
        co = T["cmap"][0]
        ntab = struct.unpack(">H", d[co + 2:co + 4])[0]
        sub = {}
        for i in range(ntab):
            p, e, off = struct.unpack(">HHI", d[co + 4 + 8 * i:co + 12 + 8 * i])
            off += co
            fmt = struct.unpack(">H", d[off:off + 2])[0]
            if p in (0, 3) and fmt in (4, 12):
                sub[(p, e, fmt)] = off
        for key in sorted(sub, key=lambda k: -k[2]):
            off = sub[key]
            fmt = key[2]
            if fmt == 12:
                self._cmap12(off)
            else:
                self._cmap4(off)
            if self.cmap:
                break

    def _cmap12(self, o):
        d = self.d
        nG = struct.unpack(">I", d[o + 12:o + 16])[0]
        for i in range(nG):
            b = o + 16 + 12 * i
            s, e, g = struct.unpack(">III", d[b:b + 12])
            if e - s > 70000:
                continue
            for c in range(s, e + 1):
                self.cmap[c] = g + (c - s)

    def _cmap4(self, o):
        d = self.d
        segX2 = struct.unpack(">H", d[o + 6:o + 8])[0]
        seg = segX2 // 2
        endO = o + 14
        startO = endO + segX2 + 2
        deltaO = startO + segX2
        rangeO = deltaO + segX2
        for i in range(seg):
            end = struct.unpack(">H", d[endO + 2 * i:endO + 2 * i + 2])[0]
            start = struct.unpack(">H", d[startO + 2 * i:startO + 2 * i + 2])[0]
            delta = struct.unpack(">h", d[deltaO + 2 * i:deltaO + 2 * i + 2])[0]
            ro = struct.unpack(">H", d[rangeO + 2 * i:rangeO + 2 * i + 2])[0]
            if start == 0xFFFF or end < start:
                continue
            for c in range(start, min(end, 0xFFFE) + 1):
                if ro == 0:
                    g = (c + delta) & 0xFFFF
                else:
                    gi = rangeO + 2 * i + ro + 2 * (c - start)
                    if gi + 2 > len(d):
                        continue
                    g = struct.unpack(">H", d[gi:gi + 2])[0]
                    if g:
                        g = (g + delta) & 0xFFFF
                if g:
                    self.cmap[c] = g

    def gid(self, ch):
        return self.cmap.get(ord(ch), 0)

    def width(self, ch, size):
        g = self.gid(ch)
        if g >= len(self.adv):
            g = 0
        return self.adv[g] * size / self.upem

    def scaled(self, v):
        return int(round(v * 1000.0 / self.upem))


# ---------------------------------------------------------------- PDF core
class PDF:
    def __init__(self):
        self.objs = [None]

    def add(self, data):
        self.objs.append(data)
        return len(self.objs) - 1

    def stream(self, extra, data, compress=True):
        if compress:
            payload = zlib.compress(data, 9)
            head = extra.rstrip()
            assert head.endswith(">>")
            head = head[:-2] + "/Filter /FlateDecode /Length %d >>" % len(payload)
        else:
            payload = data
            head = extra.rstrip()
            head = head[:-2] + "/Length %d >>" % len(payload)
        return self.add(head.encode("latin1") + b"\nstream\n" + payload +
                        b"\nendstream")

    def build(self, path, root, info=None):
        out = bytearray()
        out += b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        offsets = [0] * len(self.objs)
        for num in range(1, len(self.objs)):
            offsets[num] = len(out)
            out += b"%d 0 obj\n" % num
            out += self.objs[num]
            out += b"\nendobj\n"
        xref = len(out)
        n = len(self.objs)
        out += b"xref\n0 %d\n" % n
        out += b"0000000000 65535 f \n"
        for num in range(1, n):
            out += b"%010d 00000 n \n" % offsets[num]
        out += b"trailer\n<< /Size %d /Root %d 0 R" % (n, root)
        if info:
            out += b" /Info %d 0 R" % info
        out += b" >>\nstartxref\n%d\n%%%%EOF\n" % xref
        open(path, "wb").write(bytes(out))


# ---------------------------------------------------------------- document
class Doc:
    def __init__(self, pdf, font):
        self.pdf = pdf
        self.font = font
        self.pages = []          # list of {"ops": [...], "images": set}
        self.cur = None
        self.y = 0.0
        self.missing = set()

    # --- page management
    def new_page(self):
        self.cur = {"ops": [], "images": set()}
        self.pages.append(self.cur)
        self.y = MT
        return self.cur

    def space(self, h):
        self.y += h

    def ensure(self, h):
        if self.cur is None:
            self.new_page()
        if self.y + h > PAGE_H - MB:
            self.new_page()

    # --- text
    def _clean(self, s):
        out = []
        for ch in s:
            if ord(ch) >= 128 and self.font.gid(ch) == 0:
                self.missing.add(ch)
                ch = {"\u2212": "-", "\u2013": "-"}.get(ch, "?")
            out.append(ch)
        return "".join(out)

    def measure(self, s, size):
        return sum(self.font.width(c, size) for c in s)

    def _line_ops(self, x, y, s, size, color):
        gids = []
        for ch in s:
            g = self.font.gid(ch)
            if g == 0 and ch not in (" ", "\u3000"):
                self.missing.add(ch)
            gids.append(g)
        hx = "".join("%04X" % g for g in gids)
        return ("%.3f %.3f %.3f rg BT /F1 %.2f Tf 1 0 0 1 %.2f %.2f Tm <%s> Tj ET"
                % (color[0], color[1], color[2], size, x, PAGE_H - y, hx))

    def _tokens(self, s):
        toks = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c == " ":
                while i < n and s[i] == " ":
                    i += 1
                toks.append(("s", " "))
            elif ord(c) < 128 and (c.isalnum() or c in ".,;:()[]/-+=%'\""):
                j = i
                while (j < n and ord(s[j]) < 128
                       and (s[j].isalnum() or s[j] in ".,;:()[]/-+=%'\"")):
                    j += 1
                toks.append(("w", s[i:j]))
                i = j
            else:
                toks.append(("c", c))
                i += 1
        return toks

    def wrap(self, s, size, maxw):
        lines = []
        cur = []
        curw = 0.0
        for kind, t in self._tokens(s):
            w = self.measure(t, size)
            if curw + w > maxw and cur:
                while cur and cur[-1][0] == "s":
                    cur.pop()
                lines.append(cur)
                cur = []
                curw = 0.0
                if kind == "s":
                    continue
            if w > maxw:
                for ch in t:
                    cw = self.measure(ch, size)
                    if curw + cw > maxw and cur:
                        lines.append(cur)
                        cur = []
                        curw = 0.0
                    cur.append(("c", ch))
                    curw += cw
            else:
                cur.append((kind, t))
                curw += w
        if cur:
            lines.append(cur)
        return lines

    def body(self, s, size=10.2, leading=16.4, color=(0.11, 0.11, 0.12),
             indent=0.0, gap=6.0):
        s = self._clean(s)
        maxw = CW - indent
        for para in s.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            lines = self.wrap(para, size, maxw)
            for ln in lines:
                self.ensure(leading)
                text = "".join(t for _, t in ln)
                self.cur["ops"].append(self._line_ops(
                    ML + indent, self.y + size * 0.86, text, size, color))
                self.y += leading
            self.y += gap

    def heading(self, s, size=13.2, top=14.0, bottom=8.0):
        s = self._clean(s)
        self.ensure(top + size + bottom)
        self.y += top
        self.cur["ops"].append(self._line_ops(
            ML, self.y + size * 0.86, s, size, (0.05, 0.05, 0.06)))
        self.y += size * 1.05 + 2.5
        self.cur["ops"].append(
            "0.80 0.80 0.82 RG 0.6 w %.2f %.2f m %.2f %.2f l S"
            % (ML, PAGE_H - self.y, ML + CW, PAGE_H - self.y))
        self.y += bottom

    def caption(self, s, size=8.6, maxw=None):
        s = self._clean(s)
        lines = self.wrap(s, size, maxw or CW)
        for ln in lines:
            self.ensure(size + 5)
            text = "".join(t for _, t in ln)
            self.cur["ops"].append(self._line_ops(
                ML, self.y + size * 0.86, text, size, (0.42, 0.42, 0.44)))
            self.y += size + 4.4
        self.y += 4.0

    def figure(self, im, label, caption, disp_w=None, center=True):
        w = disp_w or CW
        h = w * im["h"] / im["w"]
        self.ensure(h + 30)
        x = ML + (CW - w) / 2.0 if center else ML
        self.cur["images"].add(im["name"])
        self.cur["ops"].append("q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q"
                               % (w, h, x, PAGE_H - self.y - h, im["name"]))
        self.y += h + 5.0
        if label:
            label = self._clean(label)
            self.cur["ops"].append(self._line_ops(
                x, self.y + 9.0, label, 9.0, (0.10, 0.10, 0.11)))
            self.y += 13.0
        if caption:
            self.caption(caption)
        self.y += 4.0

    def table(self, header, rows, widths, size=9.2, rowh=14.6, hsize=None):
        header = [self._clean(c) for c in header]
        rows = [[self._clean(c) for c in r] for r in rows]
        hsize = hsize or size
        xs = [ML]
        for w in widths[:-1]:
            xs.append(xs[-1] + w * CW)
        total = sum(widths)
        if abs(total - 1.0) > 1e-6:
            xs = [ML + sum(widths[:i]) / total * CW for i in range(len(widths))]

        def draw_header():
            if self.y + rowh * 2.2 > PAGE_H - MB:
                self.new_page()
            y0 = self.y
            for j, cell in enumerate(header):
                self.cur["ops"].append(self._line_ops(
                    xs[j] + 4, y0 + hsize * 0.86, cell, hsize,
                    (0.15, 0.15, 0.16)))
            self.y = y0 + rowh
            self.cur["ops"].append(
                "0.45 0.45 0.47 RG 0.7 w %.2f %.2f m %.2f %.2f l S"
                % (ML, PAGE_H - self.y, ML + CW, PAGE_H - self.y))

        draw_header()
        for i, row in enumerate(rows):
            if self.y + rowh > PAGE_H - MB:
                self.new_page()
                draw_header()
            for j, cell in enumerate(row):
                col = (0.16, 0.16, 0.17) if j == 0 else (0.28, 0.28, 0.30)
                self.cur["ops"].append(self._line_ops(
                    xs[j] + 4, self.y + size * 0.86, cell, size, col))
            self.y += rowh
            self.cur["ops"].append(
                "0.87 0.87 0.88 RG 0.5 w %.2f %.2f m %.2f %.2f l S"
                % (ML, PAGE_H - self.y + 1.5, ML + CW,
                   PAGE_H - self.y + 1.5))
        self.y += 8.0

    def rule(self, gap_top=4.0, gap_bottom=8.0, color="0.85 0.85 0.86"):
        self.ensure(gap_top + gap_bottom + 1)
        self.y += gap_top
        self.cur["ops"].append(
            "%s RG 0.5 w %.2f %.2f m %.2f %.2f l S"
            % (color, ML, PAGE_H - self.y, ML + CW, PAGE_H - self.y))
        self.y += gap_bottom

    def figpair(self, im1, lab1, cap1, im2, lab2, cap2):
        gap = 16.0
        w = (CW - gap) / 2.0
        h1 = w * im1["h"] / im1["w"]
        h2 = w * im2["h"] / im2["w"]
        hm = max(h1, h2)
        cap1 = self._clean(cap1)
        cap2 = self._clean(cap2)
        l1 = self.wrap(cap1, 8.2, w)
        l2 = self.wrap(cap2, 8.2, w)
        caph = max(len(l1), len(l2)) * 12.6
        self.ensure(hm + caph + 26)
        ytop = self.y
        for im, lab, hh, xx in ((im1, lab1, h1, ML),
                                (im2, lab2, h2, ML + w + gap)):
            self.cur["images"].add(im["name"])
            self.cur["ops"].append("q %.2f 0 0 %.2f %.2f %.2f cm /%s Do Q"
                                   % (w, hh, xx, PAGE_H - ytop - hh,
                                      im["name"]))
        ylab = ytop + hm + 10.0
        for lab, xx in ((lab1, ML), (lab2, ML + w + gap)):
            self.cur["ops"].append(self._line_ops(
                xx, ylab, self._clean(lab), 9.0, (0.10, 0.10, 0.11)))
        ycap = ylab + 11.0
        for lines, xx in ((l1, ML), (l2, ML + w + gap)):
            yy = ycap
            for ln in lines:
                text = "".join(t for _, t in ln)
                self.cur["ops"].append(self._line_ops(
                    xx, yy, text, 8.2, (0.42, 0.42, 0.44)))
                yy += 12.6
        self.y = ycap + caph + 6.0


# ---------------------------------------------------------------- main
def main():
    W, H, px = read_png(SRC)

    def img_crop(name, box, outw):
        x0, y0, x1, y1 = box
        w, h, c = crop_rgb(px, W, H, x0, y0, x1, y1)
        oh = int(round(outw * h / w))
        return {"name": name, "w": outw, "h": oh, "data": downscale(c, w, h, outw, oh)}

    fig1 = img_crop("Im1", (0, 0, W, H), 1152)
    fig2 = img_crop("Im2", (600, 230, 2060, 1320), 920)
    fig3 = img_crop("Im3", (560, 1010, 1210, 1440), 560)
    fig4 = img_crop("Im4", (540, 630, 1030, 1120), 460)

    ttf = TTF(FONT)
    pdf = PDF()

    # font objects
    ff = pdf.stream("<< /Length1 %d >>" % len(ttf.d), ttf.d)
    bbox = "[%d %d %d %d]" % (ttf.scaled(ttf.xMin), ttf.scaled(ttf.yMin),
                              ttf.scaled(ttf.xMax), ttf.scaled(ttf.yMax))
    desc = pdf.add((
        "<< /Type /FontDescriptor /FontName /SimHei /Flags 4 %s "
        "/ItalicAngle 0 /Ascent %d /Descent %d /CapHeight 700 /StemV 80 "
        "/FontFile2 %d 0 R >>" % (bbox, ttf.scaled(ttf.ascent),
                                  ttf.scaled(ttf.descent), ff)).encode("latin1"))

    doc = Doc(pdf, ttf)
    imids = {}
    for im in (fig1, fig2, fig3, fig4):
        imids[im["name"]] = pdf.stream(
            "<< /Type /XObject /Subtype /Image /Width %d /Height %d "
            "/ColorSpace /DeviceRGB /BitsPerComponent 8 >>"
            % (im["w"], im["h"]), im["data"])

    # ---------------- content ----------------
    doc.new_page()
    doc.y = MT + 4
    doc.cur["ops"].append(doc._line_ops(
        ML, doc.y + 20.0, doc._clean("土星系统 · 真实比例壁纸"), 21,
        (0.05, 0.05, 0.06)))
    doc.y += 34.0
    doc.cur["ops"].append(doc._line_ops(
        ML, doc.y + 10.0,
        doc._clean("图像说明 · 2560 × 1600 px · 程序化渲染 · 2026-10-04"), 9.6,
        (0.45, 0.45, 0.47)))
    doc.y += 18.0
    doc.rule(2.0, 10.0)

    doc.heading("一、概述", top=2.0)
    doc.body(
        "这张壁纸以土星系统为主体：画面中央是土星本体与完整的光环系统，八颗主要卫星按真实"
        "相对大小分布在压缩后的椭圆轨道上，每颗天体配有名牌、引线与定位圆环。背景并非装饰性"
        "星点，而是按真实天球坐标程序化绘制的星空——银河自左向右横贯画面，银心正好位于土星"
        "身后；大、小麦哲伦云、仙女座星系（M31）、猎户座大星云（M42）等真实天体按赤经赤纬"
        "投影到画面中，并带有小字标注；所有标注均绘制在轨道线之上，不会被轨道遮挡。\n\n"
        "画面遵循三条原则：其一，天体尺寸真实——所有球体按 1 px ≈ 216 km 的比例绘制"
        "（土星体积平均半径 58,232 km 对应 270 px），最小的土卫七仅约 2.2 px，用定位圆环"
        "标识；其二，轨道距离压缩——真实间距下土卫九将远在画面之外，故椭圆轨道只作示意"
        "（画面已注明 NOT TO SCALE）；其三，星空力求真实——恒星取自真实星表，银河形态参考"
        "巡天数据，而非随机噪点。")
    doc.figure(fig1, "图 1　全图：土星、八颗主要卫星与基于真实星表的银河星空。",
               "程序化渲染的土星系统全景，2560 × 1600 像素。土星位于画面中心，银心"
               "恰好藏于其后；左下方为大麦哲伦云（LMC）与小麦哲伦云（SMC）方向。")

    doc.heading("二、绘制工具与流程")
    doc.body(
        "本图由一个完全自写的纯 Python 渲染器绘制：运行环境为 Python 3.14，仅使用标准库"
        "（math、zlib、struct 等），没有使用 PIL、ImageMagick、Photoshop 等任何图形软件；"
        "PNG 文件由自写编码器直接写出，画面中的所有像素均为逐点计算生成。主要工具与脚本"
        "如下：")
    for it in [
        "· sky_prep.py（数据准备）：从 HYG v4.1 星表提取视星等 ≤ 7.5 的 25,791 颗恒星，"
        "从 OpenNGC 星表提取 133 个深空天体，并手工补充大、小麦哲伦云（NED 数据），"
        "生成两个纯文本数据文件。",
        "· sky_render.py（天空渲染模块）：实现赤道坐标→银道坐标转换、Lambert 圆柱等面积"
        "投影、恒星与深空天体绘制、银河亮度模型与标签防碰撞布局。",
        "· saturn_true_scale.py（主渲染脚本）：绘制太阳光晕、土星本体、光环、卫星、轨道、"
        "名牌与引线，完成全部合成并输出 2560 × 1600 PNG。",
        "· crop.py 与对比度增强脚本（校验工具）：对成品做局部放大、亮度增强检查，用于排查"
        "引线越线、环缝断裂、银河过渡生硬等问题。",
        "· make_doc_pdf.py（本文档）：自写 PDF 排版与生成工具，负责嵌入字体与图片。",
        "· flatten_pdf.py（PDF 栅格化工具）：将排版好的 PDF 逐页渲染为图像并重新封装，"
        "保证在不同阅读器中显示一致。",
    ]:
        doc.body(it, gap=2.0)
    doc.body(
        "渲染流程：读取星表 → 银道投影绘制银河 → 绘制 25,791 颗恒星 → 绘制 135 个深空天体 "
        "→ 叠加太阳光晕与轨道线 → 绘制深空天体标签（保证位于轨道线之上）→ 按远近顺序绘制"
        "卫星、光环、土星本体（含前后遮挡）→ 标注名牌与引线 → 叠加每三行降低 5% 亮度的"
        "扫描线 → 写出 PNG。")
    doc.heading("三、绘制方法详解")
    doc.body(
        "1. 画布与风格：画幅 2560 × 1600；背景为极暗冷色渐变（约 RGB 1~3）。主光源位于"
        "左上方，土星、光环与所有卫星的受光面均朝向左上；颜色取自实测色调（冰卫星灰白、"
        "土卫六橙色雾霾、土卫八双色反照率等）。全图叠加扫描线以统一质感。")
    doc.body(
        "2. 天球坐标与投影：恒星与深空天体的赤道坐标 (α, δ) 先转换为银道坐标 (l, b)"
        "（北银极 α = 192.85948°, δ = 27.12825°，银经零点 122.93192°），再用 Lambert "
        "圆柱等面积投影铺满画幅：x = (l + 180°) / 360° × W，y = (1 - sin b) / 2 × H。"
        "全天 360° × 180° 正好映射为整幅画面，银心位于画面中心、土星身后。")
    doc.body(
        "3. 恒星（25,791 颗）：颜色由 B-V 色指数近似黑体色温后映射为 RGB；亮度与尺寸按"
        "流量 10^(-0.4V) 缩放；亮星绘制更大的方块并叠加径向光晕。")
    doc.body(
        "4. 深空天体（135 个）：按类型分别渲染——星系按视长轴、短轴与位置角绘制柔和椭圆，"
        "大、小麦哲伦云以多频噪声叠加不规则结构与中央棒；球状星团绘制明亮核心与渐暗圆晕；"
        "疏散星团在视场内撒布星点并覆以淡雾；行星状星云为青绿色环，超新星遗迹为红色丝状，"
        "发射星云为粉红色云气，反射星云为蓝色。带标注天体自动寻找不重叠的位置；文字推迟"
        "到轨道线绘制之后写入，保证标签始终压在轨道之上、不被轨道点遮断。")
    doc.body(
        "5. 银河：亮度模型 = 银道带窄分量（σ ≈ 5.5°–9°）+ 宽晕（约占总亮度 22%）+ 银心"
        "核球增亮 - 大暗隙与煤袋星云暗尘带；以 4 px 网格配合“概率抖动”渲染，使从亮带到"
        "背景星空的过渡平滑无硬边（该处为针对暗带生硬问题的第二版修复）。")
    doc.body(
        "6. 土星本体（球面光照模型）：以体积平均半径 58,232 km 对应 270 px 定标"
        "（1 px ≈ 216 km），极向压缩系数 0.902。光线采用左上方向单光源的朗伯漫反射"
        "（ambient + diffuse），并叠加边缘变暗（limb darkening）与最外缘大气柔边，"
        "使圆面呈现球体体积感。云带按真实球面几何展开：由星环椭圆扁率 0.42 反推视线"
        "与自转轴夹角约 65°，对每个像素求其球面法线与自转轴的点积，得到纬度坐标"
        "sin φ = -sin 65°·(ey / R) + cos 65°·nz；因此所有云带都是球面上的真实弧线，"
        "与星环投影属于同一族曲线（弧度严格一致），并在可见极点附近自然收拢。颜色采用"
        " 17 段卡西尼自然色色板：蓝灰色极冠、奶油色亮区、橙棕色腰带与明亮赤道带；"
        "并叠加大气细带（双频正弦）、轻微经向抖动与环系在云顶投下的弯曲暗影"
        "（纬度约 -6° 处），最后与远/近半环按深度排序合成。")
    doc.body(
        "7. 光环：环面椭圆压缩系数 0.42、相对视线倾斜 -10°；按分区亮度逐像素绘制："
        "D（1.15–1.28 R_s）、C（1.28–1.58）、B（1.58–2.02）、卡西尼缝（2.02–2.10）、"
        "A（2.10–2.35）、恩克缝暗环（2.305–2.315）、F（2.40–2.42）；绘制顺序为“远半环 → "
        "土星本体 → 近半环”，保证行星对环的遮挡正确；每条环缝逐像素判定，避免虚线。")
    doc.body(
        "8. 卫星：真实半径按同一比例换算，小于 2.2 px 者以最小 2.2 px 圆点加定位圆环表示；"
        "位置放在与环面同方向的压缩椭圆轨道上，按远侧/近侧区分遮挡；土卫八绘制双色反照率，"
        "土卫六带橙色雾光，土卫七以斑驳纹理表示不规则外形。")
    doc.body(
        "9. 名牌与引线：每个天体配“名称 + 半径”名牌；引线自名牌指向定位圆环、恰好停在"
        "圆环外 8 px；名牌位置逐一调整，避免遮挡主体与彼此重叠。")
    doc.figpair(
        fig3, "图 2　南天星野：LMC / SMC、47 Tuc 与恒星颜色。",
        "深空天体按真实坐标、视大小与位置角绘制，标签采用防碰撞布局。",
        fig4, "图 3　光环外缘与银河带的衔接。",
        "银河雾以概率抖动平滑淡出，无生硬边界；可见 F 环与环缝细节。")
    doc.heading("四、太阳与土星")
    doc.body(
        "太阳（光晕）：画面上缘偏左的亮斑表示太阳方向与光照来源。土星距太阳约 9.6 AU，"
        "真实视角下太阳只是一颗亮星，此处以带亮核的柔和径向光晕示意，同时说明画面光照"
        "方向。")
    doc.body(
        "土星本体以体积平均半径 58,232 km 定标（赤道半径 60,268 km、极半径 54,364 km），"
        "在画面中按极向压缩系数 0.902 绘制，以贴近其约 9.8% 的扁率。光环平面相对视线倾斜"
        " -10°（真实土星自转轴倾角约 26.7°），这是为构图更舒展而作的艺术压缩；光照方向设在"
        "左上方。")
    doc.body("环系按卡西尼探测任务的实测结构建模（R_s 为土星半径 58,232 km）：")
    doc.table(
        ["环 / 缝", "范围（R_s）", "大致距离（km）"],
        [["D 环", "1.15 – 1.28", "66,970 – 74,540"],
         ["C 环", "1.28 – 1.58", "74,540 – 92,010"],
         ["B 环", "1.58 – 2.02", "92,010 – 117,630"],
         ["卡西尼缝", "2.02 – 2.10", "117,630 – 122,290"],
         ["A 环", "2.10 – 2.35", "122,290 – 136,850"],
         ["恩克缝（环缝）", "2.305 – 2.315", "134,225 – 134,810"],
         ["F 环", "2.40 – 2.42", "139,760 – 140,920"]],
        [0.34, 0.28, 0.38])
    doc.figure(fig2, "图 4　特写：土星本体、环系与土卫六（Titan，R 2575 km）。",
               "卡西尼缝、恩克缝等结构在 1 px ≈ 216 km 的分辨率下被适当加宽，以保持在缩略"
               "视图中的可读性。", disp_w=470)
    doc.body(
        "受像素尺度限制，恩克缝等细窄结构在图中被略加宽或合并；卡西尼缝在 B 环与 A 环之间"
        "呈现为明显的暗带。实测数据可参考 NASA PDS Rings Node。")

    doc.heading("五、八颗卫星（真实比例）")
    doc.body("八颗主要卫星的半径与真实轨道半径如下（数据：JPL Solar System Dynamics、"
             "IAU 2015 坐标与自转要素报告）。画面中轨道距离经过压缩，不可按图中比例换算。")
    doc.table(
        ["卫星", "平均半径（km）", "轨道半径（km）", "周期（天）"],
        [["土卫一 Mimas", "198.2", "185,540", "0.942"],
         ["土卫二 Enceladus", "252.1", "238,040", "1.370"],
         ["土卫三 Tethys", "531.1", "294,670", "1.888"],
         ["土卫四 Dione", "561.4", "377,420", "2.737"],
         ["土卫五 Rhea", "763.8", "527,070", "4.518"],
         ["土卫六 Titan", "2574.7", "1,221,870", "15.945"],
         ["土卫七 Hyperion", "135.0", "1,500,880", "21.28"],
         ["土卫八 Iapetus", "734.5", "3,560,840", "79.32"]],
        [0.34, 0.24, 0.24, 0.18])
    doc.body(
        "细节处理：土卫八按著名的“阴阳脸”着色——前导半球覆盖暗物质、后随半球明亮"
        "（卡西尼号观测结果）；土卫六带有橙色雾霾大气的柔光边缘；土卫七外形不规则、自转"
        "混沌，以斑驳纹理示意；土卫二标注其冰壳成分（H2O）。所有天体的大小均按真实半径"
        "换算，画面中的差异即真实的体量差异。")

    doc.body(
        "逐颗说明（按轨道由内到外）：\n\n"
        "· 土卫一 Mimas（R 198.2 km）：表面被巨大的 Herschel 撞击坑占据，形似“死星”。\n\n"
        "· 土卫二 Enceladus（R 252.1 km）：南极“虎纹”区喷出水汽羽流，图中标注 H2O。\n\n"
        "· 土卫三 Tethys（R 531.1 km）：拥有 Ithaca Chasma 大峡谷与 Odysseus 撞击坑。\n\n"
        "· 土卫四 Dione（R 561.4 km）：尾随半球分布明亮的“发丝状”断层地形。\n\n"
        "· 土卫五 Rhea（R 763.8 km）：多坑冰壳，土星第二大卫星。\n\n"
        "· 土卫六 Titan（R 2574.7 km）：浓密氮气大气与橙色雾霾，画面中带柔光边缘。\n\n"
        "· 土卫七 Hyperion（R 135.0 km）：海绵状不规则外形、混沌自转，以斑驳纹理表示。\n\n"
        "· 土卫八 Iapetus（R 734.5 km）：前导半球覆盖暗物质、后随半球明亮，即著名的"
        "“阴阳脸”。")

    doc.heading("六、背景深空天体全表")
    doc.body(
        "画面背景共绘制 135 个深空天体：来自 OpenNGC 星表的 133 个（Messier / NGC / IC），"
        "加上手工补充的大麦哲伦云（LMC）与小麦哲伦云（SMC）；全部按真实坐标、视大小与"
        "方位角绘制。带“标注”的为画面上有文字的天体。分类统计：星系 46（含 LMC、SMC）、"
        "球状星团 31、疏散星团 27、星云类 20（星云 7、电离氢区 6、星团+星云 6、反射星云 1）、"
        "行星状星云 5、超新星遗迹 4、星协 1、其他 1。下表列出全部天体（J2000 坐标）。")

    type_cn = {"G": "星系", "GCl": "球状星团", "OCl": "疏散星团",
               "Neb": "星云", "HII": "电离氢区", "Cl+N": "星团+星云",
               "PN": "行星状星云", "SNR": "超新星遗迹", "*Ass": "星协",
               "RfN": "反射星云", "Other": "其他"}

    def f_ra(d):
        h = d / 15.0
        H = int(h)
        m = (h - H) * 60.0
        M = int(m)
        s = int(round((m - M) * 60.0))
        if s >= 60:
            s = 0
            M += 1
        if M >= 60:
            M = 0
            H += 1
        return "%02dh%02dm%02ds" % (H, M, s)

    def f_dec(d):
        sgn = "-" if d < 0 else "+"
        a = abs(d)
        D = int(a)
        m = (a - D) * 60.0
        M = int(m)
        s = int(round((m - M) * 60.0))
        if s >= 60:
            s = 0
            M += 1
        return "%s%02d°%02d'" % (sgn, D, M)

    def f_size(a, b):
        sa = ("%.1f" % a) if a < 100 else ("%d" % int(round(a)))
        if b > 0:
            sb = ("%.1f" % b) if b < 100 else ("%d" % int(round(b)))
            return "%s' x %s'" % (sa, sb)
        return "%s'" % sa

    obj_rows = []
    for line in open(os.path.join(BASE, "sky_objects.txt"), encoding="utf-8"):
        name, otype, ra, dec, maj, minax, pa, label = \
            line.rstrip("\n").split("|")
        obj_rows.append([
            name, label or "-", type_cn.get(otype, otype),
            f_ra(float(ra)), f_dec(float(dec)),
            f_size(float(maj), float(minax)),
            ("%d°" % int(round(float(pa)))) if float(pa) else "-"])
    doc.table(
        ["编号", "标注", "类型", "赤经（J2000）", "赤纬", "视大小（角分）", "位置角"],
        obj_rows, [0.145, 0.155, 0.165, 0.165, 0.13, 0.16, 0.12],
        size=7.6, rowh=12.4, hsize=8.0)

    doc.heading("七、参考文献")
    refs = [
        "[1] ESA. The Hipparcos and Tycho Catalogues. ESA SP-1200, 1997.",
        "[2] Hoffleit D., Warren W. H. The Bright Star Catalogue, 5th rev. ed. "
        "Yale University Observatory, 1991.",
        "[3] Gliese W., Jahreiss H. Preliminary Version of the Third Catalogue of "
        "Nearby Stars. Astronomisches Rechen-Institut, 1991.",
        "[4] Nash D. HYG Database v4.1. GitHub: astronexus/HYG-Database, 2021.",
        "[5] Verga M. OpenNGC (Messier / NGC / IC 数据). GitHub: "
        "mattiaverga/OpenNGC, 2023.",
        "[6] Dreyer J. L. E. A New General Catalogue of Nebulae and Clusters of "
        "Stars. Mem. R. Astron. Soc. 49, 1–237, 1888.",
        "[7] Gaia Collaboration. Gaia Data Release 2: Mapping the Milky Way. "
        "A&A 616, A1, 2018.",
        "[8] Hauser M. G. et al. The COBE DIRBE Search for the Cosmic Infrared "
        "Background. ApJ 508, 25, 1998.",
        "[9] Porco C. C. et al. Cassini Imaging Science: Initial Results on "
        "Saturn's Rings and Small Satellites. Science 307, 1226, 2005.",
        "[10] NASA/JPL. Cassini–Huygens Mission. saturn.jpl.nasa.gov.",
        "[11] NASA PDS Rings Node. Saturnian Rings Fact Sheet. pds-rings.seti.org.",
        "[12] Archinal B. A. et al. Report of the IAU Working Group on "
        "Cartographic Coordinates and Rotational Elements: 2015. Celest. Mech. "
        "Dyn. Astron. 130, 22, 2018.",
        "[13] JPL Solar System Dynamics. Planetary Satellite Physical Parameters. "
        "ssd.jpl.nasa.gov.",
        "[14] NASA/IPAC Extragalactic Database (NED). ned.ipac.caltech.edu.",
        "[15] Spencer J. R., Denk T. Formation of the extreme albedo "
        "dichotomy of Iapetus. Icarus 209, 625, 2010.",
        "[16] Tomasko M. G. et al. Rain, winds and haze during the descent "
        "of the Huygens probe to Titan's surface. Nature 438, 765, 2005.",
    ]
    for r in refs:
        doc.body(r, size=9.4, leading=14.0, color=(0.16, 0.16, 0.18), gap=1.6)

    doc.heading("八、文件与说明")
    doc.body(
        "本图为艺术化的科学插图，而非天文照片：卫星与环的细节受像素尺度与简化模型限制，"
        "轨道距离与环面倾角经过压缩；深空天体的外观为示意性绘制，其位置、大小与方位角"
        "取自星表。\n\n"
        "输出文件：saturn-true-scale-2560x1600.png（2560 × 1600 PNG，约 830 KB）。渲染由"
        "纯 Python 程序完成（自写 PNG 编码器，无第三方图形库）；画面另叠加每三行降低 5%"
        "亮度的扫描线，以统一质感。")

    # ---------------- finalize ----------------
    # footer on every page
    total = len(doc.pages)
    for idx, pg in enumerate(doc.pages, 1):
        pg["ops"].append(
            "0.62 0.62 0.64 rg BT /F1 8.4 Tf 1 0 0 1 %.2f %.2f Tm <%s> Tj ET"
            % (PAGE_W / 2 - 4, 30,
               "".join("%04X" % ttf.gid(c) for c in "%d / %d" % (idx, total))))
        pg["ops"].append(
            "0.82 0.82 0.84 RG 0.5 w %.2f %.2f m %.2f %.2f l S"
            % (ML, PAGE_H - 40, ML + CW, PAGE_H - 40))

    # CIDFont /W for used glyphs
    used = set()
    for pg in doc.pages:
        for op in pg["ops"]:
            if " Tm <" in op:
                hx = op.split(" Tm <")[1].split(">")[0]
                for i in range(0, len(hx), 4):
                    used.add(int(hx[i:i + 4], 16))
    used.discard(0)
    gl = sorted(used)
    wparts = []
    i = 0
    while i < len(gl):
        j = i
        while j + 1 < len(gl) and gl[j + 1] == gl[j] + 1:
            j += 1
        run = gl[i:j + 1]
        wparts.append("%d [%s]" % (run[0], " ".join(str(ttf.scaled(ttf.adv[g]))
                                                     for g in run)))
        i = j + 1
    cidfont = pdf.add((
        "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /SimHei "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) "
        "/Supplement 0 >> /FontDescriptor %d 0 R /DW 1000 /W [%s] "
        "/CIDToGIDMap /Identity >>" % (desc, " ".join(wparts))).encode("latin1"))
    fid = pdf.add(("<< /Type /Font /Subtype /Type0 /BaseFont /SimHei "
                   "/Encoding /Identity-H /DescendantFonts [%d 0 R] >>"
                   % cidfont).encode("latin1"))

    # page objects
    kids = []
    for pg in doc.pages:
        content = "\n".join(pg["ops"]).encode("latin1")
        cid = pdf.stream("<< >>", content)
        xo = " ".join("/%s %d 0 R" % (n, i) for n, i in imids.items()
                      if n in pg["images"])
        res = "<< /Font << /F1 %d 0 R >>" % fid
        if xo:
            res += " /XObject << %s >>" % xo
        res += " >>"
        page = pdf.add((
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
            "/Resources %s /Contents %d 0 R >>"
            % (PAGE_W, PAGE_H, res, cid)).encode("latin1"))
        kids.append(page)
    pages = pdf.add(("<< /Type /Pages /Count %d /Kids [%s] >>"
                     % (len(kids), " ".join("%d 0 R" % k for k in kids))
                     ).encode("latin1"))
    # object 2 must be the Pages node; swap what we planned (we used fixed
    # refs /Parent 2 0 R, so object 2 has to be Pages).  Page objects were
    # just added after pages node; fix Parent references by moving.
    # Simplest: the Pages object number is `pages`; rewrite page parents.
    if pages != 2:
        for k in kids:
            pdf.objs[k] = pdf.objs[k].replace(b"/Parent 2 0 R",
                                              b"/Parent %d 0 R" % pages)
    cat = pdf.add(("<< /Type /Catalog /Pages %d 0 R >>" % pages).encode("latin1"))
    title = b"\xfe\xff" + "土星系统 · 真实比例壁纸 — 图像说明".encode("utf-16-be")
    info = pdf.add(("<< /Title <%s> /Author (anontokoy) /Creator "
                    "(pure-python procedural renderer) >>"
                    % title.hex().upper()).encode("latin1"))
    pdf.build(OUT, cat, info)
    print("written", OUT)
    if doc.missing:
        print("MISSING GLYPHS:", "".join(sorted(doc.missing)))


if __name__ == "__main__":
    main()
