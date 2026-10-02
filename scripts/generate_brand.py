"""Export the editable SVG brand assets (requires cairosvg and Pillow)."""

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "brand"
DESTINATION = ROOT / "custom_components" / "input_boolean_group" / "brand"


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, size in (
        ("icon", (256, 256)),
        ("dark_icon", (256, 256)),
        ("logo", None),
        ("dark_logo", None),
    ):
        rendered = cairosvg.svg2png(
            url=str(SOURCE / f"{name}.svg"),
            scale=4,
        )
        with Image.open(BytesIO(rendered)) as image:
            image = image.convert("RGBA")
            image = image.crop(image.getchannel("A").getbbox())
            if size is not None:
                # Center the mark in a tightly fitted square without distortion.
                side = max(image.size)
                square = Image.new("RGBA", (side, side))
                square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
                image = square
            else:
                # Home Assistant prefers a 256px short side for normal logos.
                size = (round(image.width * 256 / image.height), 256)
            for factor, suffix in ((1, ""), (2, "@2x")):
                image.resize(
                    (size[0] * factor, size[1] * factor), Image.Resampling.LANCZOS
                ).save(DESTINATION / f"{name}{suffix}.png", optimize=True)


if __name__ == "__main__":
    main()
