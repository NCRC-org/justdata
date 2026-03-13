"""
BranchSight chart renderers for magazine-style PDF reports.

Uses matplotlib to produce print-friendly PNG images returned as BytesIO buffers.
"""

import os
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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
# Color palette
# ---------------------------------------------------------------------------
NAVY = '#1e3a5f'
BAR_COLOR = '#1a8fc9'
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
# Branch trend line chart
# ---------------------------------------------------------------------------
def render_branch_trend_chart(branch_counts_by_year):
    """Render a line chart showing branch count over time.

    Args:
        branch_counts_by_year: dict mapping year (int or str) to branch count (int),
                               or list of dicts with 'Variable' and year columns.

    Returns:
        BytesIO containing PNG image bytes, or None if insufficient data.
    """
    if not branch_counts_by_year:
        return None

    years = []
    values = []

    if isinstance(branch_counts_by_year, dict):
        for k, v in branch_counts_by_year.items():
            try:
                yr = int(str(k).strip())
                if 2000 <= yr <= 2030:
                    years.append(yr)
                    values.append(int(v) if v else 0)
            except (ValueError, TypeError):
                pass
    elif isinstance(branch_counts_by_year, list):
        # Extract from summary table format: list of dicts with 'Variable' key
        # Find the "Total Branches" row
        total_row = None
        for row in branch_counts_by_year:
            var = str(row.get('Variable', '')).lower()
            if 'total' in var and 'branch' in var:
                total_row = row
                break
        if total_row is None and branch_counts_by_year:
            total_row = branch_counts_by_year[0]
        if total_row:
            for k, v in total_row.items():
                if k == 'Variable' or k == 'Net Change':
                    continue
                try:
                    yr = int(str(k).strip())
                    if 2000 <= yr <= 2030:
                        val = float(str(v).replace(',', '')) if v else 0
                        years.append(yr)
                        values.append(int(val))
                except (ValueError, TypeError):
                    pass

    if len(years) < 2:
        return None

    # Sort by year
    paired = sorted(zip(years, values))
    years, values = zip(*paired)

    fig, ax = plt.subplots(figsize=(5.0, 2.5), dpi=150)
    _apply_base_style(ax, fig)

    ax.plot(years, values, color=NAVY, linewidth=2.5, marker='o',
            markersize=6, zorder=3, markerfacecolor=NAVY, markeredgecolor='white',
            markeredgewidth=1.5)

    # Value labels on each point
    for yr, val in zip(years, values):
        label = f'{val:,}'
        ax.text(yr, val + max(values) * 0.04, label, ha='center',
                fontsize=7, color='#333', fontweight='bold')

    ax.set_title('Branch Count Over Time', fontsize=10, fontweight='bold',
                 color=NAVY, pad=6)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=8)
    ax.set_ylim(min(values) * 0.9, max(values) * 1.15)
    ax.yaxis.set_visible(False)
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#cccccc')
    ax.tick_params(axis='x', length=0)

    plt.tight_layout(pad=0.5)
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# HHI bar chart (deposit market concentration)
# ---------------------------------------------------------------------------
def render_hhi_chart(hhi_by_year_data):
    """Render bar chart of HHI values with threshold lines.

    Args:
        hhi_by_year_data: list of dicts with 'year' and 'hhi' keys.

    Returns:
        BytesIO containing PNG image bytes, or None if insufficient data.
    """
    if not hhi_by_year_data:
        return None

    years = []
    values = []
    for item in hhi_by_year_data:
        try:
            yr = int(item.get('year', 0))
            hhi = float(item.get('hhi', 0))
            if yr and hhi > 0:
                years.append(yr)
                values.append(hhi)
        except (ValueError, TypeError):
            continue

    if not years:
        return None

    # Sort by year
    paired = sorted(zip(years, values))
    years, values = zip(*paired)

    fig, ax = plt.subplots(figsize=(5.0, 2.5), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(years))
    ax.bar(x, values, color=BAR_COLOR, width=0.5, edgecolor='none')

    # Threshold lines
    max_val = max(values) if values else 500
    y_max = max(max_val * 1.3, 2800)
    ax.axhline(y=1500, color=HHI_MODERATE_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(years) - 0.5, 1530, 'Moderate (1,500)', fontsize=7,
            color=HHI_MODERATE_COLOR, ha='right')
    ax.axhline(y=2500, color=HHI_HIGH_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(years) - 0.5, 2530, 'Concentrated (2,500)', fontsize=7,
            color=HHI_HIGH_COLOR, ha='right')

    # Value labels on bars
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + max_val * 0.03, f'{int(v):,}', ha='center',
                    fontsize=8, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels([str(yr) for yr in years], fontsize=8)
    ax.set_title('Deposit Market Concentration (HHI)', fontsize=10,
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
    w = width if width is not None else (width_inches * inch if width_inches else 5.0 * inch)
    h = height if height is not None else (height_inches * inch if height_inches else 2.5 * inch)
    return Image(buf, width=w, height=h)
