# Confluence — brand exploration

An alternative identity for Input Boolean Group. Three independent signals flow
into one boolean switch. The curves make the logic diagram feel less mechanical;
the lime switch gives the mark a clear destination and memorable accent.

This concept has been adopted. Production SVG sources are in `assets/brand/`,
and the trimmed, optimized integration exports are in
`custom_components/input_boolean_group/brand/`. This directory preserves the
original exploration and presentation; use `scripts/generate_brand.py` to
regenerate the production assets.

## Assets

- `presentation.png`: presentation and comparison against the current icon.
- `icon.svg`, `dark_icon.svg`: editable vector marks, transparent backgrounds.
- `logo.svg`, `dark_logo.svg`: editable vector wordmarks, transparent backgrounds.
- Eight PNGs: icons at 256 / 512 px and logos at 512 × 128 / 1024 × 256 px.
- `generate.py`: deterministic SVG, PNG, and presentation generator.

`dark_` files are intended for dark surfaces. Unprefixed files are for light
surfaces. `@2x` denotes the double-resolution export.

## Palette

| Role | Hex |
| --- | --- |
| Deep petrol / light-mode switch | `#123D3A` |
| Light-mode signal | `#147D73` |
| Dark-mode signal / mint | `#83D8BD` |
| Active accent / lime | `#BDFB7A` |
| Light surface | `#F4F5EE` |
| Dark-mode wordmark | `#F0F8F1` |

## Regenerate

From the repository root, with CairoSVG, Pillow and native Cairo available:

```sh
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 assets/brand-exploration/generate.py
```

The SVG logos use DIN Alternate Bold with Arial / sans-serif fallbacks; install
DIN Alternate to reproduce the typography exactly. The presentation generator
uses the macOS system fonts at `/System/Library/Fonts/Supplemental/`.

Adjust geometry, palettes, or wordmark in `generate.py` to keep all outputs in
sync. Hand-editing the SVG files is possible, but regeneration overwrites them.

## Visual review

The presentation includes light/dark marks and real-size 32 / 64 px samples.
At 32 px, the three inputs, converging paths, and output switch stay distinct.
The symbol has no fine interior details, gradients, or baked-in background.
Exports were checked for expected dimensions, alpha transparency, and clipping;
both logo variants and the complete presentation were inspected visually.
