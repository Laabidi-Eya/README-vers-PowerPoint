import logging
import os
from colorthief import ColorThief
from pptx.dml.color import RGBColor
from agents.utils import luminance

logger = logging.getLogger(__name__)


def _saturation(r, g, b):
    mx, mn = max(r, g, b) / 255, min(r, g, b) / 255
    return (mx - mn) / mx if mx > 0 else 0


def branding_agent(state: dict) -> dict:
    logo_path = state.get("logo_path")

    if not logo_path or not os.path.exists(logo_path):
        logger.info("No logo provided. Using default colors.")
        return state

    try:
        ct = ColorThief(logo_path)
        palette = ct.get_palette(color_count=6, quality=1)

        candidates = [
            c for c in palette
            if luminance(*c) < 160 and _saturation(*c) < 0.85
        ]
        if not candidates:
            candidates = sorted(palette, key=lambda c: luminance(*c))

        palette_sorted = sorted(candidates, key=lambda c: luminance(*c))

        primary = palette_sorted[0]
        accent  = palette_sorted[-1]

        if luminance(*primary) > 130:
            primary = (30, 30, 50)

        all_sorted_vivid = sorted(palette, key=lambda c: _saturation(*c), reverse=True)
        if all_sorted_vivid and luminance(*all_sorted_vivid[0]) > 60:
            accent = all_sorted_vivid[0]

        brand_colors = {
            "primary": RGBColor(*primary),
            "accent":  RGBColor(*accent),
        }

        logger.info("Brand colors — primary: %s, accent: %s", primary, accent)
        return {**state, "brand_colors": brand_colors}

    except Exception as e:
        logger.warning("Branding extraction failed (%s). Using default colors.", e)
        return state
