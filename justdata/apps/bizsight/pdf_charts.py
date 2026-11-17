"""
BizSight chart renderers for magazine-style PDF reports.

Uses matplotlib to produce print-friendly PNG images returned as BytesIO buffers.
"""

import os
from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from reportlab.platypus import Image
from reportlab.lib.units import inch

# ---------------------------------------------------------------------------
# Register Georgia fonts with matplotlib
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'pdf', 'fonts')
for _fname in ('georgia.ttf', 'georgiab.ttf', 'georgiai.ttf', 'georgiaz.ttf'):
    _fpath = os.path.join(_FONT_DIR, _fname)
    if os.path.exists(_fpath):
        fm.fontManager.addfont(_fpath)

matplotlib.rcParams['font.family'] = 'Georgia'
matplotlib.rcParams['font.sans-serif'] = ['Georgia']
matplotlib.rcParams['font.serif'] = ['Georgia']

# ---------------------------------------------------------------------------
# Chart color palette
# ---------------------------------------------------------------------------
BAR_COLOR = '#1a8fc9'
NAVY = '#1e3a5f'
HHI_MODERATE_COLOR = '#e67e22'
HHI_HIGH_COLOR = '#e74c3c'


def _apply_base_style(ax, fig):
    """Apply common clean styling to axes."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.5)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.tick_params(axis='both', labelsize=8, length=3, width=0.5)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')


# ---------------------------------------------------------------------------
# HHI market concentration bar chart
# ---------------------------------------------------------------------------
def render_hhi_chart(hhi_by_year):
    """Render bar chart of HHI values with DOJ threshold lines.

    Args:
        hhi_by_year: list of dicts with 'year' and 'hhi_value' keys

    Returns:
        BytesIO containing PNG image bytes, or None if insufficient data.
    """
    if not hhi_by_year:
        return None

    # A missing year stays on the axis as a gap, never a zero or a dropped
    # year (no-data decision, 2026-11-17).
    years = []
    values = []
    for item in hhi_by_year:
        yr = item.get('year')
        if yr is None:
            continue
        val = item.get('hhi_value')
        years.append(str(int(float(yr))))
        values.append(float(val) if val is not None else None)

    present = [v for v in values if v is not None]
    if not present:
        return None

    fig, ax = plt.subplots(figsize=(4.5, 2.6), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(years))
    bar_x = [i for i, v in enumerate(values) if v is not None]
    ax.bar(bar_x, present, color=BAR_COLOR, width=0.5, edgecolor='none')

    # Threshold lines
    max_val = max(present)
    y_max = max(max_val * 1.3, 2800)
    ax.axhline(y=1500, color=HHI_MODERATE_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(years) - 0.5, 1530, 'Moderate (1,500)', fontsize=7,
            color=HHI_MODERATE_COLOR, ha='right')
    ax.axhline(y=2500, color=HHI_HIGH_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(years) - 0.5, 2530, 'Concentrated (2,500)', fontsize=7,
            color=HHI_HIGH_COLOR, ha='right')

    # Value labels on bars
    for i, v in enumerate(values):
        if v is None:
            ax.text(i, max_val * 0.03, '\u2014', ha='center', fontsize=8, color='#666666')
        elif v > 0:
            ax.text(i, v + max_val * 0.03, f'{round(v):,}', ha='center',
                    fontsize=8, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=8)
    ax.set_title('Market Concentration (HHI)', fontsize=10,
                 fontweight='bold', color=NAVY, pad=6)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_visible(False)
    ax.grid(False)

    plt.tight_layout(pad=0.5)
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Helper: BytesIO -> ReportLab Image
# ---------------------------------------------------------------------------
def chart_to_image(buf, width=None, height=None,
                   width_inches=None, height_inches=None):
    """Convert a PNG BytesIO buffer to a ReportLab Image flowable."""
    if buf is None:
        return None
    buf.seek(0)
    w = width if width is not None else (width_inches * inch if width_inches else 4.5 * inch)
    h = height if height is not None else (height_inches * inch if height_inches else 2.6 * inch)
    return Image(buf, width=w, height=h)
