import struct
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def generate_solid_color_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Builds a minimal valid PNG of a single flat color, stdlib only (no Pillow).

    Placeholder texture for the Fase 5 mock TextureProvider — a real texture
    engine is a future integration, not part of this architecture pass.
    """
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))

    row = bytes([0, *rgb * width])  # filter byte 0 (None) + RGB per pixel
    raw = row * height
    idat = _chunk(b"IDAT", zlib.compress(raw, level=6))

    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend
