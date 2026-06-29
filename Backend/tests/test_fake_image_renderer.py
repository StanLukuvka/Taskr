"""Unit tests for the deterministic fake image renderer.

These exercise the renderer module in isolation (no HTTP server), per the
test contract in ``fake-image-provider-design.md`` (task t_b052917c):
multiple IDs, sizes, and formats; non-empty output; reproducibility.
"""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = ROOT / "tools" / "fake_image_renderer.py"


def _load_renderer():
    spec = importlib.util.spec_from_file_location("fake_image_renderer", RENDERER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = _load_renderer()

# Skip the rendering tests entirely if Pillow is unavailable, but keep the
# pure-Python helper tests (color/format/validation) running regardless.
try:
    from PIL import Image  # noqa: F401

    HAS_PILLOW = True
except ImportError:  # pragma: no cover
    HAS_PILLOW = False

pillow_required = pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")


# ---------------------------------------------------------------------------
# Pure-Python helpers (no Pillow required)
# ---------------------------------------------------------------------------


def test_id_to_color_is_deterministic() -> None:
    assert renderer.id_to_color("abc") == renderer.id_to_color("abc")


def test_id_to_color_differs_per_id() -> None:
    assert renderer.id_to_color("abc") != renderer.id_to_color("xyz")


def test_id_to_color_matches_sha256_prefix() -> None:
    import hashlib

    digest = hashlib.sha256(b"hello").digest()
    assert renderer.id_to_color("hello") == (digest[0], digest[1], digest[2])


def test_id_to_color_returns_byte_range_rgb() -> None:
    r, g, b = renderer.id_to_color("any-id-here")
    for channel in (r, g, b):
        assert isinstance(channel, int)
        assert 0 <= channel <= 255


@pytest.mark.parametrize(
    "raw,expected",
    [("png", "png"), ("PNG", "png"), ("jpeg", "jpeg"), ("JPEG", "jpeg"), ("jpg", "jpeg"), ("JPG", "jpeg"), (None, "png")],
)
def test_normalize_format(raw, expected) -> None:
    assert renderer.normalize_format(raw) == expected


def test_normalize_format_rejects_unsupported() -> None:
    with pytest.raises(renderer.RenderError):
        renderer.normalize_format("webp")


def test_content_type_for() -> None:
    assert renderer.content_type_for("png") == "image/png"
    assert renderer.content_type_for("jpeg") == "image/jpeg"
    assert renderer.content_type_for("jpg") == "image/jpeg"


def test_supported_formats() -> None:
    assert renderer.supported_formats() == ("png", "jpeg")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0, -1, 2049, 100000])
def test_render_rejects_out_of_range_width(bad) -> None:
    with pytest.raises(renderer.RenderError):
        renderer.render_image("id", width=bad, height=100)


@pytest.mark.parametrize("bad", [0, -1, 2049, 100000])
def test_render_rejects_out_of_range_height(bad) -> None:
    with pytest.raises(renderer.RenderError):
        renderer.render_image("id", width=100, height=bad)


def test_render_rejects_bool_dimension() -> None:
    with pytest.raises(renderer.RenderError):
        renderer.render_image("id", width=True, height=100)


def test_render_rejects_bad_format() -> None:
    with pytest.raises(renderer.RenderError):
        renderer.render_image("id", width=100, height=100, fmt="gif")


# ---------------------------------------------------------------------------
# Rendering (Pillow required)
# ---------------------------------------------------------------------------


@pillow_required
def test_render_png_non_empty() -> None:
    data = renderer.render_image("test-id", 200, 150, "png")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # PNG magic number.
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


@pillow_required
def test_render_jpeg_non_empty() -> None:
    data = renderer.render_image("test-id", 200, 150, "jpeg")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # JPEG magic number.
    assert data[:2] == b"\xff\xd8"


@pillow_required
def test_render_jpg_alias_matches_jpeg() -> None:
    assert renderer.render_image("seed", 120, 90, "jpg") == renderer.render_image(
        "seed", 120, 90, "jpeg"
    )


@pillow_required
@pytest.mark.parametrize("fmt", ["png", "jpeg"])
@pytest.mark.parametrize("id_str", ["a", "test-id", "user_42", "LongerIdentifierString-123"])
@pytest.mark.parametrize("size", [(1, 1), (10, 10), (50, 30), (400, 300), (2048, 2048)])
def test_render_is_deterministic(id_str, size, fmt) -> None:
    width, height = size
    first = renderer.render_image(id_str, width, height, fmt)
    second = renderer.render_image(id_str, width, height, fmt)
    assert first == second
    assert len(first) > 0


@pillow_required
def test_render_dimensions_match_request() -> None:
    for width, height, fmt in [(100, 100, "png"), (640, 480, "jpeg"), (1, 1, "png"), (300, 50, "png")]:
        data = renderer.render_image("dims", width, height, fmt)
        with Image.open(io.BytesIO(data)) as img:
            assert img.size == (width, height)


@pillow_required
def test_render_format_round_trips() -> None:
    png = renderer.render_image("fmt", 64, 64, "png")
    jpeg = renderer.render_image("fmt", 64, 64, "jpeg")
    with Image.open(io.BytesIO(png)) as img:
        assert img.format == "PNG"
    with Image.open(io.BytesIO(jpeg)) as img:
        assert img.format == "JPEG"


@pillow_required
def test_render_background_uses_id_color() -> None:
    # A 1x1 image is below the text threshold, so it is pure background color.
    data = renderer.render_image("color-seed", 1, 1, "png")
    with Image.open(io.BytesIO(data)) as img:
        assert img.convert("RGB").getpixel((0, 0)) == renderer.id_to_color("color-seed")


@pillow_required
def test_render_different_ids_produce_different_output() -> None:
    a = renderer.render_image("alpha", 100, 100, "png")
    b = renderer.render_image("beta", 100, 100, "png")
    assert a != b


@pillow_required
def test_render_tiny_image_skips_text_but_renders() -> None:
    # width/height below the text threshold -> solid fill, still a valid image.
    data = renderer.render_image("tiny", 5, 5, "png")
    assert len(data) > 0
    with Image.open(io.BytesIO(data)) as img:
        assert img.size == (5, 5)
        # Every pixel should be the background color (no text drawn).
        rgb = img.convert("RGB")
        expected = renderer.id_to_color("tiny")
        pixels = list(rgb.getdata())
        assert all(px == expected for px in pixels)


@pillow_required
def test_render_default_dimensions() -> None:
    data = renderer.render_image("defaults")
    with Image.open(io.BytesIO(data)) as img:
        assert img.size == (renderer.DEFAULT_WIDTH, renderer.DEFAULT_HEIGHT)
