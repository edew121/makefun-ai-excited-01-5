#!/usr/bin/env python3
"""The Snow Globe Launches Itself.

make.fun ai-excited-01 entry: a snow globe that launches itself.
On a deep-blue winter night, a small red-and-white rocket bursts out
of its own glass dome, shattering the top as it climbs diagonally
toward the viewer -- glass shards, gold flame and speed lines flying.
Inside the globe a tiny village sleeps under warm yellow windows
while a cratered moon watches from above.

Pure Python 3 standard library; the picture is drawn procedurally
and deterministically (fixed seed), so two runs write byte-identical
PNGs. No text anywhere in the image.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261116

rng = random.Random(SEED)

buf = bytearray(W * H * 3)


def px(x, y, r, g, b):
    """Set one pixel, opaque."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    """Blend one pixel with opacity a (0..1)."""
    if a <= 0.0 or not (0 <= x < W and 0 <= y < H):
        return
    i = (y * W + x) * 3
    if a >= 1.0:
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b
        return
    ia = 1.0 - a
    buf[i] = int(r * a + buf[i] * ia + 0.5)
    buf[i + 1] = int(g * a + buf[i + 1] * ia + 0.5)
    buf[i + 2] = int(b * a + buf[i + 2] * ia + 0.5)


def span(x0, x1, y, r, g, b, a=1.0):
    """Fill an inclusive horizontal span on row y."""
    if y < 0 or y >= H:
        return
    if x0 > x1:
        x0, x1 = x1, x0
    x0 = max(0, int(x0))
    x1 = min(W - 1, int(x1))
    if x0 > x1:
        return
    if a >= 1.0:
        i0 = (y * W + x0) * 3
        buf[i0:i0 + (x1 - x0 + 1) * 3] = bytes((r, g, b)) * (x1 - x0 + 1)
    else:
        for x in range(x0, x1 + 1):
            blend(x, y, r, g, b, a)


def disc(cx, cy, rad, r, g, b, a=1.0):
    """Filled circle."""
    rad = float(rad)
    y0 = max(0, int(math.floor(cy - rad)))
    y1 = min(H - 1, int(math.ceil(cy + rad)))
    for y in range(y0, y1 + 1):
        dy = y - cy
        q = rad * rad - dy * dy
        if q < 0:
            continue
        dx = int(math.sqrt(q))
        span(cx - dx, cx + dx, y, r, g, b, a)


def ellipse(cx, cy, rx, ry, r, g, b, a=1.0):
    """Filled ellipse."""
    y0 = max(0, int(math.floor(cy - ry)))
    y1 = min(H - 1, int(math.ceil(cy + ry)))
    for y in range(y0, y1 + 1):
        dy = (y - cy) / float(ry)
        q = 1.0 - dy * dy
        if q < 0:
            continue
        dx = int(rx * math.sqrt(q))
        span(cx - dx, cx + dx, y, r, g, b, a)


def disc_vgrad(cx, cy, rad, top, bot):
    """Filled circle with a vertical colour gradient."""
    y0 = max(0, int(math.floor(cy - rad)))
    y1 = min(H - 1, int(math.ceil(cy + rad)))
    for y in range(y0, y1 + 1):
        dy = y - cy
        q = rad * rad - dy * dy
        if q < 0:
            continue
        dx = int(math.sqrt(q))
        t = (y - (cy - rad)) / (2.0 * rad)
        r = int(top[0] + (bot[0] - top[0]) * t + 0.5)
        g = int(top[1] + (bot[1] - top[1]) * t + 0.5)
        b = int(top[2] + (bot[2] - top[2]) * t + 0.5)
        span(cx - dx, cx + dx, y, r, g, b)


def vgrad_rect(x0, y0, x1, y1, top, bot):
    """Vertical gradient over a rectangle."""
    for y in range(max(0, y0), min(H - 1, y1) + 1):
        t = (y - y0) / max(1, y1 - y0)
        r = int(top[0] + (bot[0] - top[0]) * t + 0.5)
        g = int(top[1] + (bot[1] - top[1]) * t + 0.5)
        b = int(top[2] + (bot[2] - top[2]) * t + 0.5)
        span(x0, x1, y, r, g, b)


def poly(points, r, g, b, a=1.0):
    """Scanline-filled polygon (points: list of (x, y))."""
    ys = [p[1] for p in points]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(H - 1, int(math.ceil(max(ys))))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x0, yy0 = points[k]
            x1, yy1 = points[(k + 1) % n]
            if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                t = (y - yy0) / (yy1 - yy0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            span(int(math.ceil(xs[k])), int(math.floor(xs[k + 1])), y, r, g, b, a)


def line(x0, y0, x1, y1, w, r, g, b, a=1.0):
    """Thick line as a filled quad."""
    dx = x1 - x0
    dy = y1 - y0
    L = math.hypot(dx, dy)
    if L < 0.001:
        disc(x0, y0, w / 2.0, r, g, b, a)
        return
    nx = -dy / L * w / 2.0
    ny = dx / L * w / 2.0
    poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
          (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], r, g, b, a)


def arc(cx, cy, rad, a0, a1, w, r, g, b, a=1.0):
    """Arc (angles in radians, screen coords, y down) as short segments."""
    steps = max(8, int(abs(a1 - a0) * rad / 6.0))
    prev = None
    for k in range(steps + 1):
        t = a0 + (a1 - a0) * k / steps
        p = (cx + rad * math.cos(t), cy + rad * math.sin(t))
        if prev is not None:
            line(prev[0], prev[1], p[0], p[1], w, r, g, b, a)
        prev = p


def glow(cx, cy, rad, r, g, b, peak=0.5, steps=18):
    """Soft radial glow (layered translucent discs)."""
    for k in range(steps, 0, -1):
        t = k / steps
        a = peak * (1.0 - t) * (1.0 - t) * 0.28
        disc(cx, cy, rad * t, r, g, b, a)


# ------------------------------------------------------------------ scene
SKY_TOP = (8, 14, 42)
SKY_BOT = (30, 48, 96)

GLOBE_C = (512, 470)
GLOBE_R = 320


def draw_sky():
    vgrad_rect(0, 0, W - 1, H - 1, SKY_TOP, SKY_BOT)
    for _ in range(230):
        x = rng.randint(4, W - 5)
        y = rng.randint(4, 760)
        s = rng.random()
        if s < 0.55:
            px(x, y, 235, 240, 255)
        elif s < 0.85:
            disc(x, y, 1.6, 240, 244, 255)
        else:
            disc(x, y, 2.2, 250, 250, 255)
            line(x - 5, y, x + 5, y, 1.2, 220, 230, 255, 0.8)
            line(x, y - 5, x, y + 5, 1.2, 220, 230, 255, 0.8)


def draw_moon():
    glow(205, 170, 150, 245, 238, 200, peak=0.35)
    disc(205, 170, 68, 247, 241, 213)
    for (cx, cy, rr) in [(182, 148, 12), (228, 186, 16), (212, 138, 8),
                         (243, 152, 7), (186, 196, 9), (222, 208, 6)]:
        disc(cx, cy, rr, 222, 210, 172)
    disc(228, 192, 52, 232, 224, 192, 0.35)


def draw_hills():
    ellipse(180, 1060, 520, 130, 20, 33, 66)
    ellipse(880, 1080, 560, 150, 26, 42, 82)
    ellipse(180, 1005, 500, 55, 96, 118, 168, 0.55)
    ellipse(880, 1020, 540, 60, 104, 126, 176, 0.55)


def draw_base():
    # body
    poly([(196, 812), (828, 812), (800, 908), (224, 908)], 94, 52, 22)
    poly([(212, 872), (812, 872), (800, 908), (224, 908)], 74, 40, 16)
    for y in (838, 862):
        line(210, y, 814, y, 2, 60, 32, 12, 0.6)
    # brass band
    poly([(200, 816), (824, 816), (824, 828), (200, 828)], 201, 162, 39)
    # top ellipse (the globe sits on this)
    ellipse(512, 812, 316, 38, 138, 90, 40)
    ellipse(512, 810, 282, 30, 160, 106, 50)
    ellipse(512, 808, 240, 22, 178, 122, 62, 0.7)


def draw_globe():
    # glass rim, then the night sky inside the dome
    disc(GLOBE_C[0], GLOBE_C[1], GLOBE_R + 4, 168, 205, 235)
    disc_vgrad(GLOBE_C[0], GLOBE_C[1], GLOBE_R - 2, (52, 86, 138), (16, 30, 66))
    # a few tiny stars inside the dome
    for _ in range(60):
        ang = rng.uniform(0, 2.0 * math.pi)
        rr = rng.uniform(0, 290)
        x = int(GLOBE_C[0] + rr * math.cos(ang))
        y = int(GLOBE_C[1] + rr * math.sin(ang))
        if y < 660:
            px(x, y, 225, 235, 250)


def window(x, y, w=12, h=16):
    glow(x + w / 2.0, y + h / 2.0, 20, 255, 190, 80, peak=0.5)
    poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], 255, 201, 77)
    line(x + w / 2.0, y, x + w / 2.0, y + h, 1.5, 120, 70, 10, 0.8)
    line(x, y + h / 2.0, x + w, y + h / 2.0, 1.5, 120, 70, 10, 0.8)


def house(x, top, w, h):
    base = 716
    poly([(x, top + 22), (x + w, top + 22), (x + w, base), (x, base)],
         46, 32, 24)
    # roof
    poly([(x - 8, top + 24), (x + w / 2.0, top), (x + w + 8, top + 24)],
         58, 40, 30)
    # snow on the roof slopes
    line(x - 8, top + 24, x + w / 2.0, top, 5, 232, 240, 248, 0.95)
    line(x + w / 2.0, top, x + w + 8, top + 24, 5, 232, 240, 248, 0.95)
    # warm windows
    window(x + 10, top + 44)
    window(x + w - 24, top + 44)
    if w >= 90:
        window(x + w / 2.0 - 6, top + 42)


def pine(x, base, h):
    w = h * 0.55
    poly([(x - 4, base - 14), (x + 4, base - 14), (x + 4, base), (x - 4, base)],
         60, 38, 20)
    for k in range(3):
        top = base - h + k * h * 0.30
        half = w * (0.30 + 0.22 * k)
        yb = base - 12 - k * h * 0.22
        poly([(x, top), (x - half, yb), (x + half, yb)], 15, 61, 36)
    disc(x, base - h, 5, 235, 242, 250)


def draw_village():
    cx, cy = GLOBE_C
    # snow mound, clipped to the globe circle
    for y in range(688, 800):
        dy = y - 790
        q = 1.0 - (dy / 70.0) ** 2
        if q <= 0:
            continue
        mx = int(285 * math.sqrt(q))
        gy = y - cy
        gq = GLOBE_R * GLOBE_R - gy * gy
        if gq <= 0:
            continue
        gx = int(math.sqrt(gq)) - 4
        span(max(cx - mx, cx - gx), min(cx + mx, cx + gx), y, 214, 228, 244)
    # houses and pines on the mound
    pine(300, 712, 92)
    house(330, 640, 95, 76)
    pine(448, 714, 68)
    house(462, 618, 108, 98)
    pine(592, 714, 80)
    house(612, 652, 88, 64)
    pine(724, 710, 62)
    # chimney on the middle house, with smoke drifting up-right
    poly([(542, 588), (558, 588), (558, 632), (542, 632)], 58, 40, 30)
    poly([(540, 584), (560, 584), (560, 592), (540, 592)], 46, 32, 24)
    for k in range(5):
        disc(550 + k * 9, 578 - k * 16, 9 - k, 205, 212, 224, 0.30)

# ------------------------------------------------------- rocket and burst
AX = math.radians(35)  # rocket tilt from vertical, climbing up-right
COSA, SINA = math.cos(AX), math.sin(AX)
PUNCTURE = (695, 208)  # where the rocket pierces the dome
ROCKET_C = (718, 175)  # rocket centre, just outside the puncture


def rot(lx, ly, cx, cy):
    """Rotate a point from the rocket's local frame to the canvas."""
    return (cx + lx * COSA - ly * SINA, cy + lx * SINA + ly * COSA)


def rot_poly(local_pts, cx, cy):
    return [rot(x, y, cx, cy) for (x, y) in local_pts]


def draw_rocket():
    cx, cy = ROCKET_C
    # flame glow behind the tail, inside the dome
    glow(643, 281, 120, 255, 140, 40, peak=0.55)
    # flame: three nested teardrops, wide at the tail, pointed far behind
    poly(rot_poly([(-16, 78), (-30, 130), (-14, 185), (0, 215),
                   (14, 185), (30, 130), (16, 78)], cx, cy), 255, 122, 26)
    poly(rot_poly([(-11, 80), (-20, 125), (-9, 165), (0, 185),
                   (9, 165), (20, 125), (11, 80)], cx, cy), 255, 182, 39)
    poly(rot_poly([(-6, 82), (-11, 115), (-5, 145), (0, 160),
                   (5, 145), (11, 115), (6, 82)], cx, cy), 255, 243, 176)
    # fins
    poly(rot_poly([(-20, 30), (-54, 92), (-20, 88)], cx, cy), 212, 43, 43)
    poly(rot_poly([(20, 30), (54, 92), (20, 88)], cx, cy), 212, 43, 43)
    # white body
    poly(rot_poly([(-20, -70), (20, -70), (20, 70), (-20, 70)], cx, cy),
         244, 246, 250)
    # red nose cone
    poly(rot_poly([(-20, -70), (0, -118), (20, -70)], cx, cy), 212, 43, 43)
    # red band near the tail
    poly(rot_poly([(-20, 52), (20, 52), (20, 68), (-20, 68)], cx, cy),
         212, 43, 43)
    # shaded edge on the body's right side
    poly(rot_poly([(12, -70), (20, -70), (20, 70), (12, 70)], cx, cy),
         216, 222, 232, 0.8)
    # porthole
    wx, wy = rot(0, -18, cx, cy)
    disc(wx, wy, 11, 240, 244, 250)
    disc(wx, wy, 8, 150, 205, 235)
    disc(wx - 2, wy - 2, 3, 235, 248, 255)


def draw_crack():
    px_, py_ = PUNCTURE
    glow(px_, py_, 90, 190, 220, 255, peak=0.5)
    # bright star-burst at the puncture
    for k in range(8):
        ang = k * math.pi / 4.0 + 0.2
        line(px_, py_, px_ + 26 * math.cos(ang), py_ + 26 * math.sin(ang),
             3, 240, 248, 255, 0.95)
    # jagged cracks radiating across the glass
    for (ang_deg, length) in [(-90, 95), (-55, 120), (-20, 85), (10, 70),
                              (45, 60), (-130, 80), (160, 65), (120, 55),
                              (-160, 50)]:
        ang = math.radians(ang_deg)
        x, y = float(px_), float(py_)
        for _ in range(3):
            a2 = ang + rng.uniform(-0.25, 0.25)
            nx = x + (length / 3.0) * math.cos(a2)
            ny = y + (length / 3.0) * math.sin(a2)
            line(x, y, nx, ny, 2.5, 225, 240, 252, 0.9)
            x, y = nx, ny


def draw_shards():
    for _ in range(16):
        ang = math.radians(rng.uniform(-95, 15))
        dist = rng.uniform(45, 190)
        sx = PUNCTURE[0] + dist * math.cos(ang)
        sy = PUNCTURE[1] + dist * math.sin(ang)
        s = rng.uniform(7, 26)
        ra = rng.uniform(0, math.pi)
        pts = []
        for k in range(3):
            a = ra + k * 2.1
            pts.append((sx + s * math.cos(a), sy + s * 0.8 * math.sin(a)))
        poly(pts, 205, 228, 248, rng.uniform(0.55, 0.9))
    # two shards tumbling back inside the dome
    for (sx, sy, s) in [(640, 300, 14), (742, 262, 10)]:
        poly([(sx, sy - s), (sx + s, sy + s), (sx - s, sy + s)],
             205, 228, 248, 0.8)


def draw_speed_lines():
    # lines parallel to the rocket axis, trailing behind its tail
    ax_, ay_ = SINA, -COSA
    px_, py_ = COSA, SINA  # perpendicular
    tx, ty = 673, 239  # tail
    for _ in range(9):
        d = rng.uniform(-170, 170)
        if abs(d) < 48:
            continue
        gap = rng.uniform(10, 60)
        L = rng.uniform(70, 150)
        sx = tx + px_ * d - ax_ * gap
        sy = ty + py_ * d - ay_ * gap
        line(sx, sy, sx - ax_ * L, sy - ay_ * L, 2.5, 235, 242, 252, 0.45)
    # three short lines ahead of the nose
    nx, ny = rot(0, -118, ROCKET_C[0], ROCKET_C[1])
    for d in (-40, 0, 40):
        sx = nx + px_ * d + ax_ * 12
        sy = ny + py_ * d + ay_ * 12
        line(sx, sy, sx + ax_ * 55, sy + ay_ * 55, 2.5, 235, 242, 252, 0.5)


def draw_glass():
    # crescent highlight, upper left of the dome
    arc(512, 470, 296, math.radians(150), math.radians(300), 16,
        255, 255, 255, 0.22)
    arc(512, 470, 272, math.radians(170), math.radians(290), 7,
        255, 255, 255, 0.25)
    # rim
    arc(512, 470, 321, 0, math.radians(360), 4, 200, 225, 245, 0.6)
    # soft shadow along the bottom inside the dome
    arc(512, 470, 300, math.radians(30), math.radians(150), 22,
        10, 22, 52, 0.3)


def draw_snow():
    # snow drifting inside the globe
    for _ in range(150):
        ang = rng.uniform(0, 2.0 * math.pi)
        rr = rng.uniform(0, 300)
        x = 512 + rr * math.cos(ang)
        y = 470 + rr * math.sin(ang)
        if y > 690:
            continue
        disc(x, y, rng.uniform(0.8, 2.0), 240, 246, 252,
             rng.uniform(0.4, 0.9))
    # snow outside, plus wind streaks near the burst
    for _ in range(80):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, 900)
        disc(x, y, rng.uniform(1.0, 2.6), 235, 242, 252,
             rng.uniform(0.35, 0.85))
    for _ in range(14):
        x = rng.randint(560, 950)
        y = rng.randint(60, 420)
        line(x, y, x - 26, y + 34, 2, 235, 242, 252, 0.5)


def vignette():
    cx, cy = W / 2.0, H / 2.0
    for y in range(H):
        dy = (y - cy) / cy
        dy2 = dy * dy
        row = y * W * 3
        for x in range(W):
            dx = (x - cx) / cx
            d2 = dx * dx + dy2
            if d2 > 0.62:
                t = (math.sqrt(d2) - 0.787) / 0.627
                f = 1.0 - 0.30 * t * t
                i = row + x * 3
                buf[i] = int(buf[i] * f)
                buf[i + 1] = int(buf[i + 1] * f)
                buf[i + 2] = int(buf[i + 2] * f)


# ------------------------------------------------------------------- output
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def png_bytes():
    """Encode the buffer as a PNG (filter 0), falling back to filter Up
    (per-row) if the plain encoding would bust the 1 MiB gate."""
    stride = W * 3
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)
    data = _png_wrap(comp)
    if len(data) <= 950000:
        return data
    # Up filter: usually much smaller on smooth gradients.
    raw = bytearray()
    prev = bytes(stride)
    for y in range(H):
        row = buf[y * stride:(y + 1) * stride]
        raw.append(2)
        raw += bytes((a - b) & 0xFF for a, b in zip(row, prev))
        prev = row
    comp2 = zlib.compress(bytes(raw), 9)
    data2 = _png_wrap(comp2)
    return data2 if len(data2) < len(data) else data


def _png_wrap(comp):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp)
            + _chunk(b"IEND", b""))


def main():
    draw_sky()
    draw_moon()
    draw_hills()
    draw_base()
    draw_globe()
    draw_village()
    draw_rocket()
    draw_crack()
    draw_shards()
    draw_speed_lines()
    draw_glass()
    draw_snow()
    vignette()
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(png_bytes())


if __name__ == "__main__":
    main()
