import struct
import zlib

from src.infrastructure.ai_providers.mocks.solid_color_png import generate_solid_color_png


def test_generates_valid_png_header_and_dimensions():
    png_bytes = generate_solid_color_png(4, 3, (200, 100, 50))

    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png_bytes[16:24])
    assert (width, height) == (4, 3)


def test_pixel_data_round_trips_to_requested_color():
    width, height, rgb = 2, 2, (10, 20, 30)
    png_bytes = generate_solid_color_png(width, height, rgb)

    idat_start = png_bytes.index(b"IDAT") + 4
    idat_length = struct.unpack(">I", png_bytes[idat_start - 8 : idat_start - 4])[0]
    raw = zlib.decompress(png_bytes[idat_start : idat_start + idat_length])

    bytes_per_row = 1 + width * 3
    assert len(raw) == bytes_per_row * height
    for row in range(height):
        row_bytes = raw[row * bytes_per_row : (row + 1) * bytes_per_row]
        assert row_bytes[0] == 0
        assert row_bytes[1:4] == bytes(rgb)
