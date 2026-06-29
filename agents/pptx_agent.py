from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os
from datetime import datetime
from agents.utils import luminance

DARK_BLUE  = RGBColor(0x1E, 0x3A, 0x5F)
ACCENT     = RGBColor(0xF9, 0x73, 0x16)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG   = RGBColor(0xF8, 0xF9, 0xFF)
GRAY_TEXT  = RGBColor(0x33, 0x33, 0x44)
LIGHT_BLUE = RGBColor(0xCC, 0xDD, 0xFF)

W = Inches(10)
H = Inches(7.5)

_SANDBOX_GLOBALS = {
    "Inches": Inches,
    "Pt": Pt,
    "RGBColor": RGBColor,
    "PP_ALIGN": PP_ALIGN,
    "enumerate": enumerate,
    "len": len,
    "range": range,
    "int": int,
    "float": float,
    "str": str,
    "list": list,
    "bool": bool,
    "__builtins__": {},
}


def _rgb(val, default):
    if isinstance(val, (list, tuple)) and len(val) == 3:
        return RGBColor(*val)
    return default


def _ensure_contrast(fg: RGBColor, bg: RGBColor) -> RGBColor:
    if abs(luminance(*fg) - luminance(*bg)) < 60:
        return WHITE if luminance(*bg) < 128 else GRAY_TEXT
    return fg


def _fill_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _add_rect(slide, x, y, w, h, color):
    shape = slide.shapes.add_shape(1, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _textbox(slide, x, y, w, h, text, size, bold=False, color=WHITE,
             align=PP_ALIGN.CENTER, wrap=True, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(x, y, w, h)
    tf = txBox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    return tf


def _title_slide(prs, title_text, primary=DARK_BLUE, accent=ACCENT,
                 title_font="Calibri", title_size=52, title_bold=True, title_color=WHITE):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, primary)
    _add_rect(slide, 0, 0, Inches(0.18), H, accent)
    _add_rect(slide, Inches(0.5), Inches(4.6), Inches(9), Inches(0.06), accent)
    _textbox(slide, Inches(0.5), Inches(1.8), Inches(9), Inches(2.2),
             title_text, title_size, bold=title_bold, color=title_color,
             align=PP_ALIGN.CENTER, font_name=title_font)
    date_str = datetime.now().strftime("%d %B %Y")
    _textbox(slide, Inches(0.5), Inches(4.9), Inches(9), Inches(0.7),
             date_str, 16, bold=False, color=LIGHT_BLUE,
             align=PP_ALIGN.CENTER, font_name=title_font)


def _content_slide(prs, title_text, bullets, primary=DARK_BLUE, accent=ACCENT,
                   bg_color=None, text_color=None, title_font="Calibri",
                   body_font="Calibri", title_size=28, body_size=17,
                   bullet_char="▶", title_bold=True, title_color=WHITE,
                   body_bold=False):
    bg = bg_color if bg_color else LIGHT_BG
    txt = text_color if text_color else GRAY_TEXT

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fill_bg(slide, bg)

    _add_rect(slide, 0, 0, W, Inches(1.5), primary)
    _add_rect(slide, 0, Inches(1.5), W, Inches(0.08), accent)
    _add_rect(slide, 0, Inches(1.58), Inches(0.1), H - Inches(1.58), accent)
    _add_rect(slide, W - Inches(1.2), 0, Inches(1.2), Inches(1.5), primary)

    _textbox(slide, Inches(0.4), Inches(0.2), Inches(8.2), Inches(1.1),
             title_text, title_size, bold=title_bold, color=title_color,
             align=PP_ALIGN.LEFT, font_name=title_font)

    n = len(bullets)
    # Content zone: y=1.68" to y=7.3"  →  5.62" available
    CONTENT_TOP = Inches(1.68)
    CONTENT_H   = Inches(5.62)
    CONTENT_X   = Inches(0.35)
    CONTENT_W   = Inches(9.3)

    if n <= 5:
        # ── Card layout: one visual card per bullet ──────────────────────
        gap      = Inches(0.14)
        card_h   = (CONTENT_H - gap * (n - 1)) / max(n, 1)
        font_pt  = min(20, max(13, int(card_h * 72 * 0.30)))

        for i, bullet in enumerate(bullets):
            cy = CONTENT_TOP + i * (card_h + gap)

            # card background (white with slight tint)
            card_bg = slide.shapes.add_shape(1, CONTENT_X, cy, CONTENT_W, card_h)
            card_bg.fill.solid()
            card_bg.fill.fore_color.rgb = WHITE
            card_bg.line.color.rgb = RGBColor(0xE0, 0xE4, 0xED)
            card_bg.line.width = Pt(0.75)

            # left accent bar
            bar_w = Inches(0.07)
            bar = slide.shapes.add_shape(1, CONTENT_X, cy, bar_w, card_h)
            bar.fill.solid()
            bar.fill.fore_color.rgb = accent
            bar.line.fill.background()

            # bullet icon box
            icon_size = Inches(0.38)
            icon_x = CONTENT_X + bar_w + Inches(0.18)
            icon_y = cy + (card_h - icon_size) / 2
            icon_box = slide.shapes.add_shape(1, icon_x, icon_y, icon_size, icon_size)
            icon_box.fill.solid()
            icon_box.fill.fore_color.rgb = accent
            icon_box.line.fill.background()
            tf_ic = icon_box.text_frame
            tf_ic.paragraphs[0].alignment = PP_ALIGN.CENTER
            run_ic = tf_ic.paragraphs[0].add_run()
            run_ic.text = str(i + 1)
            run_ic.font.size = Pt(int(font_pt * 0.7))
            run_ic.font.bold = True
            run_ic.font.color.rgb = WHITE
            run_ic.font.name = body_font

            # text
            text_x = icon_x + icon_size + Inches(0.18)
            text_w = CONTENT_X + CONTENT_W - text_x - Inches(0.2)
            text_margin = (card_h - Pt(font_pt).inches * 1.4) / 2
            tb = slide.shapes.add_textbox(text_x, cy + text_margin, text_w, card_h - text_margin * 2)
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = bullet
            run.font.size = Pt(font_pt)
            run.font.bold = body_bold
            run.font.color.rgb = txt
            run.font.name = body_font

    else:
        # ── Classic text box, vertically centered ────────────────────────
        max_size, min_size = max(body_size + 3, 20), 12
        ideal_per = CONTENT_H * 72 / n          # pt per bullet
        font_pt   = max(min_size, min(max_size, int(ideal_per * 0.38)))
        line_h    = font_pt * 1.45
        spacing   = max(6.0, min(ideal_per - line_h, 32.0))

        est_h     = Inches((line_h * n + spacing * (n - 1)) / 72)
        y_start   = CONTENT_TOP + max(Inches(0.1), (CONTENT_H - est_h) / 2)

        txBox2 = slide.shapes.add_textbox(CONTENT_X + Inches(0.1), y_start,
                                          CONTENT_W - Inches(0.1), est_h + Inches(0.3))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True

        for i, bullet in enumerate(bullets):
            p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
            p.space_before = Pt(0 if i == 0 else int(spacing))

            dot = p.add_run()
            dot.text = bullet_char + "  "
            dot.font.size = Pt(int(font_pt * 0.65))
            dot.font.color.rgb = accent
            dot.font.name = body_font
            dot.font.bold = True

            run = p.add_run()
            run.text = bullet
            run.font.size = Pt(font_pt)
            run.font.bold = body_bold
            run.font.color.rgb = txt
            run.font.name = body_font


def _exec_pptx_code(prs: Presentation, code: str) -> None:
    import logging
    _log = logging.getLogger(__name__)
    for block in code.split("\n# ---BLOCK---\n"):
        block = block.strip()
        if not block:
            continue
        sandbox = {**_SANDBOX_GLOBALS, "prs": prs}
        try:
            exec(block, sandbox)  # noqa: S102
        except Exception as e:
            _log.warning("execute_pptx_code block failed: %s\nCode:\n%s", e, block)


def pptx_agent(state: dict) -> dict:
    slides_plan = state["slides_plan"]
    readme_content = state.get("readme_content", "")

    brand = state.get("brand_colors") or {}
    dp = state.get("design_params", {})

    primary    = _rgb(dp.get("primary_color"), brand.get("primary", DARK_BLUE))
    accent     = _rgb(dp.get("accent_color"),  brand.get("accent",  ACCENT))
    bg_color   = _rgb(dp.get("bg_color"),   None)
    text_color = _rgb(dp.get("text_color"), None)

    title_font         = dp.get("title_font",  "Calibri")
    body_font          = dp.get("body_font",   "Calibri")
    cover_title_size   = int(dp.get("title_size", 52))
    content_title_size = int(dp.get("title_size", 28))
    body_size          = int(dp.get("body_size",  17))
    bullet_char        = dp.get("bullet_char", "▶")
    title_bold         = bool(dp.get("title_bold", True))
    body_bold          = bool(dp.get("body_bold", False))
    title_color        = _rgb(dp.get("title_color"), WHITE)

    raw_title = next((l.strip().lstrip("#").strip() for l in readme_content.splitlines() if l.strip()), "Présentation")
    title = slides_plan.get("title") or raw_title
    if not title or title == "TITRE_A_REMPLIR":
        title = raw_title

    if dp.get("title_color"):
        effective_title_color = title_color
    else:
        effective_title_color = _ensure_contrast(WHITE, primary)

    logo_path = state.get("logo_path")

    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H

    _title_slide(prs, title, primary, accent,
                 title_font=title_font, title_size=cover_title_size,
                 title_bold=title_bold, title_color=effective_title_color)

    for slide_data in slides_plan["slides"]:
        _content_slide(
            prs, slide_data["title"], slide_data["bullets"],
            primary=primary, accent=accent,
            bg_color=bg_color, text_color=text_color,
            title_font=title_font, body_font=body_font,
            title_size=content_title_size, body_size=body_size,
            bullet_char=bullet_char, title_bold=title_bold,
            title_color=effective_title_color, body_bold=body_bold
        )

    if logo_path and os.path.exists(logo_path):
        pos = dp.get("logo_position", "top-right")
        lw, lh = Inches(1.1), Inches(0.7)
        positions = {
            "top-right":    (W - lw - Inches(0.1), Inches(0.1)),
            "top-left":     (Inches(0.1), Inches(0.1)),
            "bottom-right": (W - lw - Inches(0.1), H - lh - Inches(0.1)),
            "bottom-left":  (Inches(0.1), H - lh - Inches(0.1)),
        }
        lx, ly = positions.get(pos, positions["top-right"])
        for slide in prs.slides:
            slide.shapes.add_picture(logo_path, lx, ly, lw, lh)

    pptx_code = state.get("pptx_code")
    if pptx_code:
        _exec_pptx_code(prs, pptx_code)

    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join("output", f"presentation_{timestamp}.pptx")
    prs.save(output_path)

    def _to_hex(c):
        try:
            return "#{:02X}{:02X}{:02X}".format(c[0], c[1], c[2])
        except Exception:
            return "#1E3A5F"

    actual_bg  = bg_color   if bg_color   else LIGHT_BG
    actual_txt = text_color if text_color else GRAY_TEXT

    return {**state, "output_path": output_path, "effective_colors": {
        "primary":    _to_hex(primary),
        "accent":     _to_hex(accent),
        "bg":         _to_hex(actual_bg),
        "text":       _to_hex(actual_txt),
        "title_text": _to_hex(effective_title_color),
    }}
