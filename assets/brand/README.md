# Confluence — Input Boolean Group

Three independent signals converge into a single boolean switch. The approved
identity uses petrol, mint and lime, with separate light and dark palettes.

The four SVG files here are editable sources. The integration ships the eight
PNG exports in `custom_components/input_boolean_group/brand/`.

## Regenerate

With CairoSVG, Pillow and native Cairo installed, run from the repository root:

```sh
python3 scripts/generate_brand.py
```

On macOS with Homebrew Cairo, if Python cannot find the native library:

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 scripts/generate_brand.py
```

The SVG wordmarks use DIN Alternate Bold with Arial / sans-serif fallbacks.
Install DIN Alternate to reproduce the checked-in typography exactly.

## Export contract

- PNG, RGBA transparency, lossless optimized compression.
- `icon.png` and `dark_icon.png`: 256 × 256 pixels.
- `icon@2x.png` and `dark_icon@2x.png`: 512 × 512 pixels.
- `logo.png` and `dark_logo.png`: landscape, short side 256 pixels.
- `logo@2x.png` and `dark_logo@2x.png`: twice the base dimensions, short side 512 pixels.
- Transparent margins are trimmed; icons retain only the spacing required to
  center the non-square mark in a square image without distortion.
- Unprefixed assets target white backgrounds; `dark_` assets target dark backgrounds.

The directory and filenames follow the
[Home Assistant local brand images documentation](https://developers.home-assistant.io/docs/core/integration/brand_images/),
[Home Assistant image specification](https://github.com/home-assistant/brands#image-specification),
and [HACS brand asset requirements](https://hacs.xyz/docs/publish/integration/#brand-assets).
Local brand images are supported by Home Assistant 2026.3 and newer without
manifest configuration. The integration retains its existing 2026.2 minimum
because the branding does not affect runtime compatibility.

The original concept presentation is preserved in `assets/brand-exploration/`.
