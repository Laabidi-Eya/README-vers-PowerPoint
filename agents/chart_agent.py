import re
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Regex patterns ────────────────────────────────────────────────
_PCT_RE  = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')
_NUM_RE  = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*'
    r'(secondes?|minutes?|heures?|jours?|semaines?|mois|ans?|fois|x'
    r'|ms|ko|mo|go|tb|k€|m€|€|\$|£|users?|clients?|employe|person|projets?'
    r'|tickets?|bugs?|tests?|deploys?)',
    re.IGNORECASE
)

_STOP_WORDS = {
    'le', 'la', 'les', 'de', 'du', 'des', 'et', 'en', 'un', 'une',
    'par', 'sur', 'avec', 'pour', 'the', 'of', 'to', 'a', 'in', 'and',
    'or', 'at', 'from', 'by', 'our', 'your', 'this', 'that', 'is', 'are',
}


def _short_label(text: str, max_len: int = 28) -> str:
    """Extract a short readable label from a bullet text."""
    # Remove leading symbols/numbers
    text = re.sub(r'^[\d\W]+', '', text).strip()
    # Take first meaningful segment (before — : , or after key verbs)
    for sep in ('—', '–', ':', ',', ';'):
        if sep in text:
            parts = text.split(sep)
            candidate = parts[0].strip()
            if 4 < len(candidate) <= max_len:
                return candidate
    words = text.split()
    result, length = [], 0
    for w in words:
        if length + len(w) > max_len:
            break
        result.append(w)
        length += len(w) + 1
    return ' '.join(result) if result else text[:max_len]


def _extract_chart_data(slides: list) -> dict | None:
    """
    Scan all slides for numerical data.
    Returns the best candidate: {'slide_idx', 'labels', 'values', 'unit', 'title'}
    or None if no usable data found.
    """
    best = None

    for slide_idx, slide in enumerate(slides):
        bullets = slide.get('bullets', [])
        pct_points, num_points = [], []

        for bullet in bullets:
            # Percentage matches
            pct_matches = _PCT_RE.findall(bullet)
            if pct_matches:
                val = float(pct_matches[0].replace(',', '.'))
                label = _short_label(bullet)
                pct_points.append((label, val))

            # Numeric + unit matches
            num_matches = _NUM_RE.findall(bullet)
            if num_matches and not pct_matches:
                val = float(num_matches[0][0].replace(',', '.'))
                unit = num_matches[0][1]
                label = _short_label(bullet)
                num_points.append((label, val, unit))

        # Prefer percentages (cleaner chart), need at least 2 points
        if len(pct_points) >= 2:
            candidate = {
                'slide_idx': slide_idx,
                'title': slide.get('title', ''),
                'labels': [p[0] for p in pct_points],
                'values': [p[1] for p in pct_points],
                'unit': '%',
                'chart_type': 'pie' if len(pct_points) <= 4 else 'bar',
            }
            if best is None or len(pct_points) > len(best['values']):
                best = candidate

        elif len(num_points) >= 2 and best is None:
            unit = num_points[0][2]
            # Only use if same unit
            if all(p[2].lower().rstrip('s') == unit.lower().rstrip('s') for p in num_points):
                best = {
                    'slide_idx': slide_idx,
                    'title': slide.get('title', ''),
                    'labels': [p[0] for p in num_points],
                    'values': [p[1] for p in num_points],
                    'unit': unit,
                    'chart_type': 'bar',
                }

    return best


def _generate_chart(chart_data: dict, primary_hex: str, accent_hex: str,
                    bg_hex: str, output_dir: str) -> str:
    """Generate a matplotlib chart and return the saved PNG path."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    def hex_to_rgb(h: str):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

    primary_rgb = hex_to_rgb(primary_hex)
    accent_rgb  = hex_to_rgb(accent_hex)
    bg_rgb      = hex_to_rgb(bg_hex)

    labels = chart_data['labels']
    values = chart_data['values']
    unit   = chart_data['unit']
    ctype  = chart_data['chart_type']
    n      = len(labels)

    # Build color palette: interpolate between primary and accent
    colors = []
    for i in range(n):
        t = i / max(n - 1, 1)
        r = primary_rgb[0] + t * (accent_rgb[0] - primary_rgb[0])
        g = primary_rgb[1] + t * (accent_rgb[1] - primary_rgb[1])
        b = primary_rgb[2] + t * (accent_rgb[2] - primary_rgb[2])
        colors.append((r, g, b))

    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=bg_rgb)
    ax.set_facecolor(bg_rgb)

    if ctype == 'pie':
        wedges, texts, autotexts = ax.pie(
            values, labels=None, colors=colors,
            autopct='%1.0f%%', startangle=140,
            wedgeprops={'linewidth': 2, 'edgecolor': bg_rgb},
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(11)
            at.set_fontweight('bold')
            at.set_color('white')

        # Legend on the right
        legend_patches = [
            mpatches.Patch(color=colors[i], label=labels[i])
            for i in range(n)
        ]
        ax.legend(handles=legend_patches, loc='center left',
                  bbox_to_anchor=(0.88, 0.5), fontsize=10,
                  frameon=False,
                  labelcolor=[primary_rgb] * n)

    else:
        # Horizontal bar chart
        y_pos = np.arange(n)
        bars = ax.barh(y_pos, values, color=colors, height=0.55,
                       edgecolor='none')

        # Value labels inside/outside bars
        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            x_pos = bar.get_width()
            offset = max_val * 0.02
            ax.text(x_pos + offset, bar.get_y() + bar.get_height() / 2,
                    f'{val:g}{unit}', va='center', ha='left',
                    fontsize=10, fontweight='bold',
                    color=primary_rgb)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10, color=primary_rgb)
        ax.invert_yaxis()
        ax.set_xlabel(unit, fontsize=10, color=primary_rgb)
        ax.xaxis.set_tick_params(labelcolor=primary_rgb, labelsize=9)

        # Subtle grid
        ax.xaxis.grid(True, linestyle='--', alpha=0.3, color=primary_rgb)
        ax.set_axisbelow(True)

        # Remove spines
        for spine in ['top', 'right', 'left']:
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color(primary_rgb)
        ax.spines['bottom'].set_alpha(0.3)

    plt.tight_layout(pad=1.2)

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f'chart_{timestamp}.png')
    fig.savefig(path, dpi=150, bbox_inches='tight',
                facecolor=bg_rgb, transparent=False)
    plt.close(fig)
    logger.info("Chart saved to %s", path)
    return path


def chart_agent(state: dict) -> dict:
    slides = state.get('slides_plan', {}).get('slides', [])
    if not slides:
        return state

    chart_data = _extract_chart_data(slides)
    if not chart_data:
        logger.info("No numerical data found — skipping chart generation.")
        return state

    # Resolve colors from effective_colors or defaults
    ec = state.get('effective_colors') or {}
    primary_hex = ec.get('primary', '#1E3A5F')
    accent_hex  = ec.get('accent',  '#F97316')
    bg_hex      = ec.get('bg',      '#F8F9FF')

    # Also check brand_colors if effective_colors not yet set
    if primary_hex == '#1E3A5F':
        bc = state.get('brand_colors') or {}
        if bc.get('primary'):
            c = bc['primary']
            primary_hex = '#{:02X}{:02X}{:02X}'.format(c[0], c[1], c[2])
        if bc.get('accent'):
            c = bc['accent']
            accent_hex = '#{:02X}{:02X}{:02X}'.format(c[0], c[1], c[2])

    try:
        chart_path = _generate_chart(chart_data, primary_hex, accent_hex,
                                     bg_hex, 'output')
        logger.info("Chart generated — type=%s, points=%d",
                    chart_data['chart_type'], len(chart_data['values']))
        return {**state, 'chart_data': {**chart_data, 'image_path': chart_path}}
    except Exception as e:
        logger.warning("Chart generation failed: %s", e)
        return state
