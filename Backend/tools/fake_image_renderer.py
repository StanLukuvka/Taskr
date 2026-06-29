"""Deterministic placeholder image renderer.

Generates a placeholder image from an ID string and requested dimensions.
The output is deterministic: the same ID + width + height + format always
produces byte-identical image content.

This module is the renderer half of the fake image provider (see
``fake-image-provider-design.md``). It is intentionally decoupled from the
HTTP server (``fake_image_provider.py``) so it can be unit-tested in isolation.

Visual content (per the design contract):
  1. Solid background fill, color derived from ``sha256(id)[:3]``.
  2. The ID string rendered centered (slightly above center), white text.
  3. The dimensions (e.g. ``400x300``) rendered below the ID, smaller, light gray.

A semi-transparent dark rectangle is drawn behind the text for contrast so the
white text stays legible on any background color. For images too small to hold
text (width < 20 or height < 20), the text overlay is skipped and only the solid
color fill is returned.

Pillow is imported lazily inside :func:`render_image` so that importing this
module does not require Pillow to be installed; callers that never render an
image (e.g. the credit-only endpoints) keep working without the dependency.
"""

from __future__ import annotations

import hashlib
import io

# Public constants describing the supported parameter space. The HTTP server
# validates against these; they live here so the renderer is the single source
# of truth for what it can produce.
MIN_DIMENSION = 1
MAX_DIMENSION = 2048
DEFAULT_WIDTH = 400
DEFAULT_HEIGHT = 300

# Canonical output format -> Pillow save format + MIME type.
_FORMATS: dict[str, tuple[str, str]] = {
    "png": ("PNG", "image/png"),
    "jpeg": ("JPEG", "image/jpeg"),
}
# Accepted aliases mapped to their canonical name.
_FORMAT_ALIASES: dict[str, str] = {
    "png": "png",
    "jpeg": "jpeg",
    "jpg": "jpeg",
}

# Below this size in either dimension, text is unreadable, so we skip it.
_MIN_TEXT_DIMENSION = 20

# Text colors.
_ID_TEXT_COLOR = (255, 255, 255)
_DIM_TEXT_COLOR = (204, 204, 204)  # #CCCCCC

# JPEG quality (lossy). Fixed so output stays deterministic.
_JPEG_QUALITY = 85


class RenderError(ValueError):
    """Raised for invalid renderer arguments (bad dimensions or format)."""


def supported_formats() -> tuple[str, ...]:
    """Return the canonical output formats, in a stable order."""
    return ("png", "jpeg")


def normalize_format(fmt: str | None) -> str:
    """Normalize a requested format to its canonical name.

    Accepts case-insensitive ``png``, ``jpeg``, and ``jpg`` (alias for jpeg).
    Returns the canonical name (``png`` or ``jpeg``).

    Raises:
        RenderError: if the format is not supported.
    """
    if fmt is None:
        return "png"
    key = fmt.strip().lower()
    canonical = _FORMAT_ALIASES.get(key)
    if canonical is None:
        raise RenderError("format must be one of: png, jpeg")
    return canonical


def content_type_for(fmt: str) -> str:
    """Return the MIME type for a canonical format name."""
    canonical = normalize_format(fmt)
    return _FORMATS[canonical][1]


def id_to_color(id_str: str) -> tuple[int, int, int]:
    """Map an ID string to a deterministic RGB background color.

    Uses the first three bytes of ``sha256(id)`` so the same ID always maps to
    the same color.
    """
    digest = hashlib.sha256(id_str.encode("utf-8")).digest()
    return (digest[0], digest[1], digest[2])


def _validate_dimension(value: int, name: str) -> None:
    # Reject bools explicitly (bool is a subclass of int).
    if isinstance(value, bool) or not isinstance(value, int):
        raise RenderError(
            f"{name} must be an integer between {MIN_DIMENSION} and {MAX_DIMENSION}"
        )
    if value < MIN_DIMENSION or value > MAX_DIMENSION:
        raise RenderError(
            f"{name} must be an integer between {MIN_DIMENSION} and {MAX_DIMENSION}"
        )


def _load_font(size: int):
    """Load Pillow's default bitmap font at the requested size.

    Falls back to the unsized default font on older Pillow versions that do not
    accept a ``size`` argument.
    """
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Very old Pillow: load_default() takes no size argument.
        return ImageFont.load_default()


def _text_size(draw, text: str, font) -> tuple[int, int]:
    """Return the (width, height) of ``text`` rendered with ``font``."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return (right - left, bottom - top)


def _draw_centered_text(
    image,
    *,
    id_str: str,
    width: int,
    height: int,
) -> None:
    """Draw the ID and dimension text centered on the image with a contrast box."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)

    # Scale font sizes with the image, clamped to readable bounds.
    id_font_size = max(10, min(width, height) // 8)
    id_font_size = min(id_font_size, 64)
    dim_font_size = max(8, id_font_size // 2)

    id_font = _load_font(id_font_size)
    dim_font = _load_font(dim_font_size)

    dim_text = f"{width}x{height}"

    id_w, id_h = _text_size(draw, id_str, id_font)
    dim_w, dim_h = _text_size(draw, dim_text, dim_font)

    gap = max(2, id_h // 4)
    block_h = id_h + gap + dim_h
    block_w = max(id_w, dim_w)

    # Vertical block centered slightly above the middle.
    block_top = (height - block_h) // 2

    id_x = (width - id_w) // 2
    id_y = block_top
    dim_x = (width - dim_w) // 2
    dim_y = block_top + id_h + gap

    # Contrast rectangle behind the text block. Semi-transparent dark fill so
    # the white/gray text is legible on any background. We composite via an
    # RGBA overlay to get the transparency, then flatten back to RGB.
    pad_x = max(4, block_w // 10)
    pad_y = max(3, block_h // 10)
    box = (
        max(0, (width - block_w) // 2 - pad_x),
        max(0, block_top - pad_y),
        min(width, (width + block_w) // 2 + pad_x),
        min(height, block_top + block_h + pad_y),
    )

    overlay = image.copy()
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(box, fill=(0, 0, 0))
    # Blend the dark box at ~45% opacity for a subtle scrim.
    image_blend = _blend(image, overlay, 0.45)
    image.paste(image_blend, (0, 0))

    draw = ImageDraw.Draw(image)
    draw.text((id_x, id_y), id_str, fill=_ID_TEXT_COLOR, font=id_font)
    draw.text((dim_x, dim_y), dim_text, fill=_DIM_TEXT_COLOR, font=dim_font)


def _blend(base, overlay, alpha: float):
    """Alpha-blend ``overlay`` over ``base`` (both RGB) -> new RGB image."""
    from PIL import Image

    return Image.blend(base, overlay, alpha)


def render_image(
    id_str: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fmt: str = "png",
) -> bytes:
    """Render a deterministic placeholder image and return the encoded bytes.

    Args:
        id_str: identifier used as the deterministic seed (background color +
            text overlay).
        width: image width in pixels (1..2048).
        height: image height in pixels (1..2048).
        fmt: output format -- ``png``, ``jpeg``, or ``jpg`` (alias for jpeg).

    Returns:
        The encoded image as raw bytes. Identical inputs always produce
        byte-identical output.

    Raises:
        RenderError: if dimensions are out of range or the format is unsupported.
        RuntimeError: if Pillow is not installed.
    """
    canonical = normalize_format(fmt)
    _validate_dimension(width, "width")
    _validate_dimension(height, "height")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - exercised when Pillow absent
        raise RuntimeError(
            "Pillow is required for image rendering but is not installed"
        ) from exc

    background = id_to_color(id_str)
    image = Image.new("RGB", (width, height), background)

    if width >= _MIN_TEXT_DIMENSION and height >= _MIN_TEXT_DIMENSION:
        _draw_centered_text(image, id_str=id_str, width=width, height=height)

    buffer = io.BytesIO()
    pil_format = _FORMATS[canonical][0]
    if pil_format == "JPEG":
        image.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
    else:
        image.save(buffer, format="PNG")
    return buffer.getvalue()
