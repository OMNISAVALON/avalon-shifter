"""Процедурный SDF-генератор матовой иконки и сглаженных элементов UI для Avalon.Shifter."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import zlib

DEFAULT_ICON_PATH = Path(__file__).with_name("avalon_shifter.ico")

BG_VOID_RGB = (26, 29, 35)      # #1A1D23
BG_CARD_RGB = (33, 37, 45)      # #21252D

TELEPORT_PHASES: tuple[float, ...] = (0.16, 0.34, 0.50, 0.66, 0.84)
PHOTONIC_WAVE_FRAMES: int = 9


def _clamp01(v: float) -> float:
    if v <= 0.0:
        return 0.0
    if v >= 1.0:
        return 1.0
    return v


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_rgb(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp01(t)
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Точное евклидово расстояние от точки до отрезка (для субпиксельного сглаживания)."""
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay
    h = _clamp01((pax * bax + pay * bay) / denom) if denom > 0.0 else 0.0
    return math.hypot(pax - bax * h, pay - bay * h)


def _sd_rounded_box(px: float, py: float, half_w: float, half_h: float, radius: float) -> float:
    """Signed Distance Function для прямоугольника со скруглёнными углами."""
    r = min(radius, half_w, half_h)
    qx = abs(px) - (half_w - r)
    qy = abs(py) - (half_h - r)
    ox = max(qx, 0.0)
    oy = max(qy, 0.0)
    return math.hypot(ox, oy) + min(max(qx, qy), 0.0) - r


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)


def _encode_png(width: int, height: int, raw_scanlines: bytearray | bytes, *, compress_level: int = 6) -> bytes:
    compressed = zlib.compress(bytes(raw_scanlines), level=compress_level)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )


def _blend_pixel_rgb(
    dst_r: float,
    dst_g: float,
    dst_b: float,
    src: tuple[int, int, int],
    alpha: float,
) -> tuple[float, float, float]:
    a = _clamp01(alpha)
    if a <= 0.0:
        return dst_r, dst_g, dst_b
    inv = 1.0 - a
    return (
        dst_r * inv + src[0] * a,
        dst_g * inv + src[1] * a,
        dst_b * inv + src[2] * a,
    )


def _render_emblem_rgba(size: int, bg_rgb: tuple[int, int, int] | None) -> bytes:
    """Рендерит сглаженную матово-обсидиановую эмблему с сатиновым золотым отливом."""
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    max_r = size * 0.455
    aa = 1.45 / max_r

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            dx = (x - cx) / max_r
            dy = (y - cy) / max_r

            # Плавный суперэллипс (squircle степени 3.6)
            squircle = (abs(dx) ** 3.6 + abs(dy) ** 3.6) ** (1.0 / 3.6)
            outer_cov = _clamp01((1.0 - squircle) / aa + 0.5)

            # Если рисуем для UI поверх известного фона, начинаем с него; для ICO — прозрачный фон
            if bg_rgb is None:
                alpha_out = outer_cov
                r, g, b = 19.0, 20.0, 23.0
            else:
                alpha_out = 1.0
                r, g, b = float(bg_rgb[0]), float(bg_rgb[1]), float(bg_rgb[2])

            if outer_cov > 0.0:
                # Диагональный матовый сатиновый отлив от #1C1E23 к #121316
                sheen = _clamp01(0.5 - 0.35 * (dx + dy))
                body_c = _lerp_rgb((18, 19, 22), (31, 33, 38), sheen)

                # Тонкая матово-золотая фаска по краю (#C5A880 сверху-слева -> #78664E снизу-справа)
                bevel_t = _clamp01(0.55 - 0.42 * (dx + dy))
                gold_rim = _lerp_rgb((120, 102, 78), (197, 168, 128), bevel_t)
                rim_cov = _clamp01((squircle - 0.875) / aa + 0.5) * _clamp01((0.985 - squircle) / aa + 0.5)

                # Тонкое внутреннее кольцо приглушённой бронзы (#3A352E)
                radial = math.hypot(dx, dy)
                inner_ring_cov = _clamp01((0.025 - abs(radial - 0.69)) / aa + 0.5)

                # Минималистичный сглаженный шеврон и золотой штрих основания
                d_left = _sd_segment(dx, dy, -0.34, 0.05, 0.0, -0.31)
                d_right = _sd_segment(dx, dy, 0.0, -0.31, 0.34, 0.05)
                d_chevron = min(d_left, d_right)
                stroke_r = 0.072 if size >= 32 else 0.092
                chevron_cov = _clamp01((stroke_r - d_chevron) / aa + 0.5)

                d_base = _sd_segment(dx, dy, -0.21, 0.27, 0.21, 0.27)
                base_r = 0.058 if size >= 32 else 0.078
                base_cov = _clamp01((base_r - d_base) / aa + 0.5)

                if bg_rgb is None:
                    r, g, b = float(body_c[0]), float(body_c[1]), float(body_c[2])
                else:
                    r, g, b = _blend_pixel_rgb(r, g, b, body_c, outer_cov)

                r, g, b = _blend_pixel_rgb(r, g, b, gold_rim, rim_cov * 0.92 * outer_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (58, 53, 46), inner_ring_cov * 0.85 * outer_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (234, 230, 223), chevron_cov * outer_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (197, 168, 128), base_cov * 0.95 * outer_cov)

            raw.append(int(_clamp01(r / 255.0) * 255))
            raw.append(int(_clamp01(g / 255.0) * 255))
            raw.append(int(_clamp01(b / 255.0) * 255))
            raw.append(int(_clamp01(alpha_out) * 255))

    return _encode_png(size, size, raw)


def _render_frame_png(size: int) -> bytes:
    """Рисует кадр прозрачной .ico иконки с антиалиасингом."""
    return _render_emblem_rgba(size, bg_rgb=None)


def render_emblem_png(size: int = 44, bg_rgb: tuple[int, int, int] = BG_VOID_RGB) -> bytes:
    """Сглаженная эмблема для шапки окна Avalon.Shifter."""
    return _render_emblem_rgba(size, bg_rgb=bg_rgb)


def render_app_icon_png(size: int = 128) -> bytes:
    """Прозрачный PNG-значок произвольного размера (16..512px) для расширений, PWA и ОС."""
    target = max(16, min(512, int(size)))
    if target <= 128:
        return _render_emblem_rgba(target, bg_rgb=None)

    base_n = 128
    base_png = _render_emblem_rgba(base_n, bg_rgb=None)
    pos = 8
    idat_chunks: list[bytes] = []
    while pos + 8 <= len(base_png):
        clen = struct.unpack(">I", base_png[pos : pos + 4])[0]
        ctag = base_png[pos + 4 : pos + 8]
        cdata = base_png[pos + 8 : pos + 8 + clen]
        pos += 12 + clen
        if ctag == b"IDAT":
            idat_chunks.append(cdata)
    raw_base = zlib.decompress(b"".join(idat_chunks))
    src_stride = 1 + base_n * 4
    rows_rgba = [raw_base[y * src_stride + 1 : (y + 1) * src_stride] for y in range(base_n)]
    x_map = [(x * base_n) // target for x in range(target)]

    out = bytearray()
    for y in range(target):
        out.append(0)
        src_row = rows_rgba[(y * base_n) // target]
        for sx in x_map:
            off = sx * 4
            out.extend(src_row[off : off + 4])
    return _encode_png(target, target, out)


def _sd_mode_glyph(nx: float, ny: float, kind: str) -> float:
    """Нормализованный SDF пиктограммы внутри кольца режима."""
    if kind == "single_shift":
        segs = (
            (0.0, -0.37, -0.35, -0.01),
            (-0.35, -0.01, -0.15, -0.01),
            (-0.15, -0.01, -0.15, 0.35),
            (-0.15, 0.35, 0.15, 0.35),
            (0.15, 0.35, 0.15, -0.01),
            (0.15, -0.01, 0.35, -0.01),
            (0.35, -0.01, 0.0, -0.37),
        )
    elif kind == "developer_guard":
        segs = (
            (-0.23, -0.21, -0.43, 0.0),
            (-0.43, 0.0, -0.23, 0.21),
            (0.07, -0.27, -0.07, 0.27),
            (0.23, -0.21, 0.43, 0.0),
            (0.43, 0.0, 0.23, 0.21),
        )
    else:
        segs = (
            (-0.24, 0.35, 0.0, -0.19),
            (0.24, 0.35, 0.0, -0.19),
            (-0.14, 0.13, 0.14, 0.13),
            (-0.23, -0.37, 0.23, -0.37),
        )
    d = 1e9
    for ax, ay, bx, by in segs:
        seg_d = _sd_segment(nx, ny, ax, ay, bx, by)
        if seg_d < d:
            d = seg_d
    return d


def render_mode_dial_png(
    active: bool,
    size: int = 56,
    bg_rgb: tuple[int, int, int] = BG_CARD_RGB,
    kind: str = "auto_switch",
) -> bytes:
    """Идеально сглаженное матовое кольцо индикатора режима со встроенным векторным глифом."""
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    radius = size * 0.41
    inv_r = 1.0 / max(1.0, radius)
    aa = 1.3
    glyph_hw = max(0.056, 1.35 * inv_r)
    glyph_aa = 1.2 * inv_r

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            px = x - cx
            py = y - cy
            dist = math.hypot(px, py)
            in_cov = _clamp01((radius - dist) / aa + 0.5)
            ring_cov = _clamp01((1.5 - abs(dist - radius)) / aa + 0.5)
            inner_ring_cov = _clamp01((0.85 - abs(dist - (radius - 4.8))) / aa + 0.5)

            glyph_cov = 0.0
            if dist <= radius * 0.72:
                gd = _sd_mode_glyph(px * inv_r, py * inv_r, kind) - glyph_hw
                glyph_cov = _clamp01(-gd / glyph_aa + 0.5)

            r, g, b = float(bg_rgb[0]), float(bg_rgb[1]), float(bg_rgb[2])
            if active:
                fill_c = (42, 41, 40)
                t_gold = _clamp01(0.5 - 0.35 * ((px + py) / max(1.0, radius * 2.0)))
                rim_c = _lerp_rgb((152, 130, 96), (206, 179, 132), t_gold)
                glyph_c = _lerp_rgb((210, 190, 152), (232, 214, 180), t_gold)
                r, g, b = _blend_pixel_rgb(r, g, b, fill_c, in_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (90, 80, 66), inner_ring_cov * 0.65)
                r, g, b = _blend_pixel_rgb(r, g, b, rim_c, ring_cov * 0.96)
                r, g, b = _blend_pixel_rgb(r, g, b, glyph_c, glyph_cov * 0.98)
            else:
                r, g, b = _blend_pixel_rgb(r, g, b, (37, 41, 49), in_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (64, 69, 79), ring_cov * 0.94)
                r, g, b = _blend_pixel_rgb(r, g, b, (140, 146, 158), glyph_cov * 0.94)

            raw.extend((int(r), int(g), int(b), 255))

    return _encode_png(size, size, raw)


def render_pill_switch_png(
    active: bool,
    width: int = 48,
    height: int = 26,
    bg_rgb: tuple[int, int, int] = BG_CARD_RGB,
) -> bytes:
    """Сглаженный капсульный переключатель со сферическим ползунком."""
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    half_w = width / 2.0 - 2.6
    half_h = height / 2.0 - 2.6
    rad = half_h
    aa = 1.25

    knob_x = (half_w - half_h) if active else -(half_w - half_h)
    knob_r = half_h - 2.2

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        py = y - cy
        for x in range(width):
            px = x - cx
            sd_pill = _sd_rounded_box(px, py, half_w, half_h, rad)
            pill_cov = _clamp01(-sd_pill / aa + 0.5)
            rim_cov = _clamp01((1.2 - abs(sd_pill)) / aa + 0.5)

            d_knob = math.hypot(px - knob_x, py)
            knob_cov = _clamp01((knob_r - d_knob) / aa + 0.5)

            r, g, b = float(bg_rgb[0]), float(bg_rgb[1]), float(bg_rgb[2])
            if active:
                r, g, b = _blend_pixel_rgb(r, g, b, (84, 73, 57), pill_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (178, 155, 118), rim_cov * 0.92)
                knob_shade = _clamp01(0.55 - 0.3 * (py / max(1.0, knob_r)))
                knob_c = _lerp_rgb((214, 208, 198), (232, 227, 218), knob_shade)
                r, g, b = _blend_pixel_rgb(r, g, b, knob_c, knob_cov)
            else:
                r, g, b = _blend_pixel_rgb(r, g, b, (44, 48, 57), pill_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, (68, 74, 85), rim_cov * 0.92)
                r, g, b = _blend_pixel_rgb(r, g, b, (154, 160, 172), knob_cov)

            raw.extend((int(r), int(g), int(b), 255))

    return _encode_png(width, height, raw)


def _render_box_with_scanline_replication(
    width: int,
    height: int,
    radius: int,
    bg_rgb: tuple[int, int, int],
    fill_top: tuple[int, int, int],
    fill_bottom: tuple[int, int, int],
    border_top: tuple[int, int, int],
    border_bottom: tuple[int, int, int],
) -> bytes:
    """Быстрый SDF-рендерер идеально сглаженных карточек и кнопок с градиентным кантом."""
    r_corner = min(radius, width // 2, height // 2)
    left_cap_w = min(width, r_corner + 4)
    right_cap_w = min(width, r_corner + 4)
    mid_w = max(0, width - left_cap_w - right_cap_w)

    half_w = width / 2.0 - 2.2
    half_h = height / 2.0 - 2.2
    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0
    aa = 1.25

    def _pixel_at(x: int, y: int, ty: float) -> bytes:
        px = x - cx
        py = y - cy
        sd = _sd_rounded_box(px, py, half_w, half_h, float(r_corner))
        in_cov = _clamp01(-sd / aa + 0.5)
        border_cov = _clamp01((1.05 - abs(sd)) / aa + 0.5)

        fill_c = _lerp_rgb(fill_top, fill_bottom, ty)
        border_c = _lerp_rgb(border_top, border_bottom, ty)

        rr, gg, bb = float(bg_rgb[0]), float(bg_rgb[1]), float(bg_rgb[2])
        rr, gg, bb = _blend_pixel_rgb(rr, gg, bb, fill_c, in_cov)
        rr, gg, bb = _blend_pixel_rgb(rr, gg, bb, border_c, border_cov * 0.92)
        return bytes((int(rr), int(gg), int(bb), 255))

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        ty = y / max(1, height - 1)
        if mid_w == 0:
            for x in range(width):
                raw.extend(_pixel_at(x, y, ty))
        else:
            for x in range(left_cap_w):
                raw.extend(_pixel_at(x, y, ty))
            mid_px = _pixel_at(left_cap_w, y, ty)
            raw.extend(mid_px * mid_w)
            for x in range(width - right_cap_w, width):
                raw.extend(_pixel_at(x, y, ty))

    return _encode_png(width, height, raw)


def render_rounded_button_png(
    width: int,
    height: int,
    primary: bool = False,
    hover: bool = False,
    pressed: bool = False,
    bg_rgb: tuple[int, int, int] = BG_CARD_RGB,
) -> bytes:
    """Сглаженная скруглённая кнопка (обычная / наведение / тактильное нажатие)."""
    if primary:
        if pressed:
            fill_top = (164, 140, 99)
            fill_bot = (188, 162, 118)
            border_top = (224, 199, 154)
            border_bot = (172, 148, 108)
        elif hover:
            fill_top = (218, 192, 146)
            fill_bot = (186, 160, 116)
            border_top = (230, 206, 162)
            border_bot = (156, 132, 96)
        else:
            fill_top = (205, 179, 134)
            fill_bot = (174, 148, 106)
            border_top = (216, 192, 148)
            border_bot = (142, 120, 86)
    else:
        if pressed:
            fill_top = (34, 38, 46)
            fill_bot = (44, 48, 58)
            border_top = (196, 170, 124)
            border_bot = (142, 122, 88)
        elif hover:
            fill_top = (52, 57, 68)
            fill_bot = (44, 48, 58)
            border_top = (134, 118, 90)
            border_bot = (84, 77, 67)
        else:
            fill_top = (43, 47, 56)
            fill_bot = (37, 41, 49)
            border_top = (64, 69, 80)
            border_bot = (50, 54, 64)

    return _render_box_with_scanline_replication(
        width=width,
        height=height,
        radius=9,
        bg_rgb=bg_rgb,
        fill_top=fill_top,
        fill_bottom=fill_bot,
        border_top=border_top,
        border_bottom=border_bot,
    )


def render_rounded_card_png(
    width: int,
    height: int,
    radius: int = 14,
    gold_tint: bool = False,
    bg_rgb: tuple[int, int, int] = BG_VOID_RGB,
) -> bytes:
    """Сглаженная бархатисто-обсидиановая карточка с мягким кантом."""
    if gold_tint:
        fill_top = (38, 41, 49)
        fill_bot = (33, 36, 44)
        border_top = (88, 79, 64)
        border_bot = (50, 52, 60)
    else:
        fill_top = (36, 40, 48)
        fill_bot = (32, 35, 43)
        border_top = (54, 59, 69)
        border_bot = (43, 47, 56)

    return _render_box_with_scanline_replication(
        width=width,
        height=height,
        radius=radius,
        bg_rgb=bg_rgb,
        fill_top=fill_top,
        fill_bottom=fill_bot,
        border_top=border_top,
        border_bottom=border_bot,
    )


def build_ico_bytes(sizes: tuple[int, ...] = (64, 48, 32, 16)) -> bytes:
    """Формирует бинарное содержимое .ico с PNG-кадрами в 4 разрешениях."""
    frames = [(s, _render_frame_png(s)) for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    entries = []
    payloads = []
    for s, png_data in frames:
        dim = 0 if s >= 256 else s
        entry = struct.pack(
            "<BBBBHHII",
            dim,
            dim,
            0,
            0,
            1,
            32,
            len(png_data),
            offset,
        )
        entries.append(entry)
        payloads.append(png_data)
        offset += len(png_data)
    return header + b"".join(entries) + b"".join(payloads)


def _sd_arc_semicircle(
    px: float,
    py: float,
    cx: float,
    cy: float,
    radius: float,
    side: str = "right",
) -> float:
    """Точное SDF полуокружности (right для R, bottom для U)."""
    dx = px - cx
    dy = py - cy
    if side == "right":
        if dx >= 0.0:
            return abs(math.hypot(dx, dy) - radius)
        return min(math.hypot(dx, dy - radius), math.hypot(dx, dy + radius))
    # bottom
    if dy >= 0.0:
        return abs(math.hypot(dx, dy) - radius)
    return min(math.hypot(dx + radius, dy), math.hypot(dx - radius, dy))


def _sd_letter(nx: float, ny: float, letter: str) -> float:
    """Нормализованный векторный SDF глифа буквы R, U, E, N (в ячейке [-0.5..0.5] x [-0.8..0.8])."""
    ch = letter.upper()
    if ch == "R":
        return min(
            _sd_segment(nx, ny, -0.44, -0.76, -0.44, 0.76),
            _sd_segment(nx, ny, -0.44, -0.76, 0.06, -0.76),
            _sd_segment(nx, ny, -0.44, 0.02, 0.06, 0.02),
            _sd_arc_semicircle(nx, ny, 0.06, -0.37, 0.39, side="right"),
            _sd_segment(nx, ny, 0.04, 0.02, 0.47, 0.76),
        )
    if ch == "U":
        return min(
            _sd_segment(nx, ny, -0.44, -0.76, -0.44, 0.28),
            _sd_segment(nx, ny, 0.44, -0.76, 0.44, 0.28),
            _sd_arc_semicircle(nx, ny, 0.0, 0.28, 0.44, side="bottom"),
        )
    if ch == "E":
        return min(
            _sd_segment(nx, ny, -0.42, -0.76, -0.42, 0.76),
            _sd_segment(nx, ny, -0.42, -0.76, 0.45, -0.76),
            _sd_segment(nx, ny, -0.42, -0.02, 0.32, -0.02),
            _sd_segment(nx, ny, -0.42, 0.76, 0.45, 0.76),
        )
    if ch == "N":
        return min(
            _sd_segment(nx, ny, -0.44, -0.76, -0.44, 0.76),
            _sd_segment(nx, ny, -0.44, -0.76, 0.44, 0.76),
            _sd_segment(nx, ny, 0.44, -0.76, 0.44, 0.76),
        )
    return 1e9


def _badge_palette(code: str, active: bool) -> tuple[
    tuple[int, int, int],
    tuple[int, int, int],
    tuple[int, int, int],
    tuple[int, int, int],
    tuple[int, int, int],
]:
    if not active:
        return (40, 43, 51), (56, 60, 70), (105, 110, 122), (142, 148, 162), (208, 212, 220)
    if code == "RU":
        return (18, 20, 26), (34, 37, 46), (186, 154, 102), (242, 210, 146), (255, 247, 226)
    return (236, 232, 224), (252, 250, 246), (178, 148, 96), (222, 192, 134), (12, 14, 18)


def _render_badge_common(
    code: str,
    active: bool,
    flow_recording: bool,
    size: int,
    bg_rgb: tuple[int, int, int] | None,
    *,
    scale_y: float = 1.0,
    scan_glow: float = 0.0,
) -> bytes:
    cx = (size - 1) / 2.0
    cy = (size - 1) / 2.0
    max_r = size * 0.488
    aa = 1.38 / max_r
    body_lo, body_hi, rim_lo, rim_hi, text_c = _badge_palette(code, active)

    sx = 0.365
    sy = 0.560
    left_cx = -0.375
    right_cx = 0.375
    stroke_rad = 0.098 if size >= 32 else 0.118
    inv_sy = 1.0 / max(0.08, scale_y)

    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            dx = (x - cx) / max_r
            dy = (y - cy) / max_r
            dy_s = dy * inv_sy

            squircle = (abs(dx) ** 3.8 + abs(dy) ** 3.8) ** (1.0 / 3.8)
            outer_cov = _clamp01((1.0 - squircle) / aa + 0.5)

            if bg_rgb is None:
                alpha_out = outer_cov
                r, g, b = float(body_lo[0]), float(body_lo[1]), float(body_lo[2])
            else:
                alpha_out = 1.0
                r, g, b = float(bg_rgb[0]), float(bg_rgb[1]), float(bg_rgb[2])

            if outer_cov > 0.0:
                sheen = _clamp01(0.5 - 0.35 * (dx + dy))
                body_c = _lerp_rgb(body_lo, body_hi, sheen)
                rim_t = _clamp01(0.55 - 0.42 * (dx + dy))
                rim_c = _lerp_rgb(rim_lo, rim_hi, rim_t)
                rim_cov = _clamp01((squircle - 0.895) / aa + 0.5) * _clamp01((0.992 - squircle) / aa + 0.5)

                txt_cov = 0.0
                if abs(dy_s) <= 1.05:
                    d_l = _sd_letter((dx - left_cx) / sx, dy_s / sy, code[0]) * sx
                    d_r = _sd_letter((dx - right_cx) / sx, dy_s / sy, code[1]) * sx
                    d_txt = min(d_l, d_r)
                    txt_cov = _clamp01((stroke_rad - d_txt) / aa + 0.5) * _clamp01(scale_y * 1.15)

                if bg_rgb is None:
                    r, g, b = float(body_c[0]), float(body_c[1]), float(body_c[2])
                else:
                    r, g, b = _blend_pixel_rgb(r, g, b, body_c, outer_cov)

                r, g, b = _blend_pixel_rgb(r, g, b, rim_c, rim_cov * 0.96 * outer_cov)
                r, g, b = _blend_pixel_rgb(r, g, b, text_c, txt_cov * outer_cov)

                if scan_glow > 0.0:
                    # Золотая фотонная полоса телепортации + квантовое сканирование
                    beam_half = 0.055 + 0.095 * scan_glow
                    beam_cov = _clamp01((beam_half - abs(dy)) / aa + 0.5) * (0.45 + 0.55 * scan_glow)
                    core_star = _clamp01((0.26 * scan_glow - math.hypot(dx * 0.55, dy * 1.6)) / aa + 0.5)
                    scan_stripe = 1.0 if ((y & 1) == 0) else 0.32
                    r, g, b = _blend_pixel_rgb(r, g, b, (238, 198, 122), beam_cov * scan_stripe * outer_cov)
                    r, g, b = _blend_pixel_rgb(r, g, b, (255, 248, 224), core_star * scan_glow * outer_cov)
                    r, g, b = _blend_pixel_rgb(r, g, b, (242, 210, 146), rim_cov * scan_glow * 0.85 * outer_cov)

            if flow_recording:
                dot_dist = math.hypot(dx - 0.75, dy + 0.75)
                dot_border = _clamp01((0.21 - dot_dist) / aa + 0.5)
                dot_core = _clamp01((0.14 - dot_dist) / aa + 0.5)
                if dot_border > 0.0:
                    r, g, b = _blend_pixel_rgb(r, g, b, (18, 19, 24), dot_border)
                    r, g, b = _blend_pixel_rgb(r, g, b, (246, 198, 96), dot_core)
                    if bg_rgb is None:
                        alpha_out = max(alpha_out, dot_border)

            raw.append(int(_clamp01(r / 255.0) * 255))
            raw.append(int(_clamp01(g / 255.0) * 255))
            raw.append(int(_clamp01(b / 255.0) * 255))
            raw.append(int(_clamp01(alpha_out) * 255))

    return _encode_png(size, size, raw)


def render_tray_layout_badge_png(
    layout: str = "RU",
    active: bool = True,
    flow_recording: bool = False,
    size: int = 64,
    bg_rgb: tuple[int, int, int] | None = None,
) -> bytes:
    """Рендерит крупный, контрастный, максимально читаемый значок раскладки RU / EN для трея."""
    code = "RU" if str(layout or "").upper().startswith("RU") else "EN"
    return _render_badge_common(
        code=code,
        active=active,
        flow_recording=flow_recording,
        size=size,
        bg_rgb=bg_rgb,
        scale_y=1.0,
        scan_glow=0.0,
    )


def render_tray_teleport_frame_png(
    from_layout: str,
    to_layout: str,
    phase: float,
    active: bool = True,
    flow_recording: bool = False,
    size: int = 32,
    bg_rgb: tuple[int, int, int] | None = None,
) -> bytes:
    """Рендерит кадр технологичной фотонной телепортации раскладки RU ⇄ EN (phase 0.0..1.0)."""
    p = _clamp01(float(phase))
    c_from = "RU" if str(from_layout or "").upper().startswith("RU") else "EN"
    c_to = "RU" if str(to_layout or "").upper().startswith("RU") else "EN"

    if p < 0.45:
        t = p / 0.45
        scale_y = max(0.14, 1.0 - 0.86 * (t * t))
        scan_glow = 0.25 + 0.70 * t
        return _render_badge_common(
            code=c_from,
            active=active,
            flow_recording=flow_recording,
            size=size,
            bg_rgb=bg_rgb,
            scale_y=scale_y,
            scan_glow=scan_glow,
        )
    if p <= 0.55:
        # Пик сингулярности 432 Гц — чистый золотой фотонный горизонт
        return _render_badge_common(
            code=c_to,
            active=active,
            flow_recording=flow_recording,
            size=size,
            bg_rgb=bg_rgb,
            scale_y=0.08,
            scan_glow=1.0,
        )
    t = (p - 0.55) / 0.45
    scale_y = max(0.14, 0.14 + 0.86 * (1.0 - (1.0 - t) ** 2))
    scan_glow = max(0.0, 0.90 * (1.0 - t))
    return _render_badge_common(
        code=c_to,
        active=active,
        flow_recording=flow_recording,
        size=size,
        bg_rgb=bg_rgb,
        scale_y=scale_y,
        scan_glow=scan_glow,
    )


def build_tray_layout_ico_bytes(
    layout: str = "RU",
    active: bool = True,
    flow_recording: bool = False,
    sizes: tuple[int, ...] = (64, 32, 16),
) -> bytes:
    """Формирует мультиразмерный .ico для значка раскладки в системном трее."""
    frames = [
        (s, render_tray_layout_badge_png(layout=layout, active=active, flow_recording=flow_recording, size=s))
        for s in sizes
    ]
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    entries = []
    payloads = []
    for s, png_data in frames:
        dim = 0 if s >= 256 else s
        entries.append(struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png_data), offset))
        payloads.append(png_data)
        offset += len(png_data)
    return header + b"".join(entries) + b"".join(payloads)


def ensure_app_icon(ico_path: Path | None = None, force: bool = False) -> Path:
    """Создаёт файл иконки avalon_shifter.ico, если он отсутствует, устарел или передан force=True."""
    target = Path(ico_path) if ico_path else DEFAULT_ICON_PATH
    if not force and target.exists() and target.stat().st_size > 64:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(build_ico_bytes((64, 48, 32, 16)))
    return target


def render_photonic_wave_frame_png(
    width: int,
    height: int,
    progress: float,
    *,
    origin_nx: float = 0.5,
    origin_ny: float = 0.5,
    primary: bool = False,
    radius: int = 9,
    shape: str = "rounded_box",
) -> bytes:
    """Рендерит один кадр сглаженного RGBA фотонного золотого импульса (жидкий волновой фронт без пиксельных кругов)."""
    w = max(8, int(width))
    h = max(8, int(height))
    t = _clamp01(progress)
    ease = 1.0 - (1.0 - t) ** 3

    cx = (w - 1) * 0.5
    cy = (h - 1) * 0.5
    ox = _clamp01(origin_nx) * (w - 1)
    oy = _clamp01(origin_ny) * (h - 1)

    max_d = max(
        math.hypot(ox, oy),
        math.hypot((w - 1) - ox, oy),
        math.hypot(ox, (h - 1) - oy),
        math.hypot((w - 1) - ox, (h - 1) - oy),
    )
    wave_r = 3.5 + ease * (max_d * 0.92 + 4.0)
    band = max(5.5, min(w, h) * 0.24 + ease * 6.5)
    inv_2band2 = 1.0 / (2.0 * band * band)
    bloom_r = wave_r * 0.62 + 5.0
    inv_2bloom2 = 1.0 / (2.0 * bloom_r * bloom_r)
    fade = (math.sin(math.pi * max(0.05, min(0.98, t))) ** 0.55) * ((1.0 - t) ** 1.15)

    circle_r = min(w, h) * 0.41
    if shape == "pill":
        half_w = w / 2.0 - 2.6
        half_h = h / 2.0 - 2.6
        corner_r = half_h
    else:
        half_w = w / 2.0 - 2.2
        half_h = h / 2.0 - 2.2
        corner_r = float(min(radius, w // 2, h // 2))

    raw = bytearray()
    for y in range(h):
        raw.append(0)
        py = y - cy
        dy = y - oy
        for x in range(w):
            px = x - cx
            if shape == "circle":
                sd = math.hypot(px, py) - circle_r
            else:
                sd = _sd_rounded_box(px, py, half_w, half_h, corner_r)

            clip = _clamp01(-sd / 1.35 + 0.5)
            if clip <= 0.0:
                raw.extend((0, 0, 0, 0))
                continue

            dist = math.hypot(x - ox, dy)
            dr = dist - wave_r
            crest = math.exp(-(dr * dr) * inv_2band2)
            bloom = math.exp(-(dist * dist) * inv_2bloom2) * 0.34
            rim = math.exp(-((sd + 1.4) ** 2) / 3.2) * crest * 0.65

            energy = _clamp01((crest * 0.48 + bloom * 0.26 + rim * 0.40) * fade * clip)
            if energy <= 0.004:
                raw.extend((0, 0, 0, 0))
                continue

            if primary:
                col = (250, 236, 206)
            else:
                col = _lerp_rgb((226, 198, 146), (248, 232, 196), crest)
            raw.extend((col[0], col[1], col[2], int(energy * 255)))

    return _encode_png(w, h, raw, compress_level=1)
