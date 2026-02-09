"""
LendSight chart renderers for magazine-style PDF reports.

Uses matplotlib to produce print-friendly PNG images returned as BytesIO buffers.
Includes both full-size charts and compact mini-charts for inline use.
"""

from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from reportlab.platypus import Image
from reportlab.lib.units import inch


# ---------------------------------------------------------------------------
# Chart color palettes
# ---------------------------------------------------------------------------
CENSUS_COLORS = ['#4472C4', '#548235', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5']
BAR_COLOR = '#1a8fc9'
NAVY = '#1e3a5f'
TEAL = '#00a4d6'
GREEN = '#27ae60'
RED = '#c0392b'
ORANGE = '#e67e22'
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


def _apply_mini_style(ax, fig):
    """Apply compact styling for mini charts."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.4)
    ax.spines['bottom'].set_linewidth(0.4)
    ax.tick_params(axis='both', labelsize=6, length=2, width=0.4)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')


# ---------------------------------------------------------------------------
# Census demographics grouped bar chart (full-size)
# ---------------------------------------------------------------------------
def render_census_demographics_chart(census_data, counties=None):
    """Render grouped bar chart showing race/ethnicity population by time period."""
    if not census_data:
        return None

    race_keys = [
        ('white_percentage', 'White'),
        ('black_percentage', 'Black'),
        ('hispanic_percentage', 'Hispanic'),
        ('asian_percentage', 'Asian'),
        ('native_american_percentage', 'Native American'),
        ('multi_racial_percentage', 'Multi-Racial'),
    ]

    period_data = {}
    period_order = ['2010 Census', '2020 Census']
    target_counties = counties or list(census_data.keys())

    for county_name in target_counties:
        county_info = census_data.get(county_name, {})
        time_periods = county_info.get('time_periods', {})
        for period_key, period_info in time_periods.items():
            label = period_info.get('year', period_key)
            demographics = period_info.get('demographics', {})
            if not demographics:
                continue
            if label not in period_data:
                period_data[label] = {rk[1]: [] for rk in race_keys}
                if label not in period_order:
                    period_order.append(label)
            for key, display in race_keys:
                val = demographics.get(key, 0)
                if val:
                    period_data[label][display].append(val)

    periods_to_plot = [p for p in period_order if p in period_data]
    if not periods_to_plot:
        return None

    race_labels = [rk[1] for rk in race_keys]
    avg_data = {}
    for period in periods_to_plot:
        avgs = []
        for race in race_labels:
            vals = period_data[period].get(race, [])
            avgs.append(sum(vals) / len(vals) if vals else 0)
        avg_data[period] = avgs

    non_zero_mask = [i for i, race in enumerate(race_labels)
                     if any(avg_data[p][i] >= 1.0 for p in periods_to_plot)]
    race_labels = [race_labels[i] for i in non_zero_mask]
    for p in periods_to_plot:
        avg_data[p] = [avg_data[p][i] for i in non_zero_mask]

    if not race_labels:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(race_labels))
    n_periods = len(periods_to_plot)
    bar_width = 0.25
    offsets = [i - (n_periods - 1) / 2 for i in range(n_periods)]

    for i, period in enumerate(periods_to_plot):
        bars = ax.bar(x + offsets[i] * bar_width, avg_data[period], bar_width,
                      label=period, color=CENSUS_COLORS[i % len(CENSUS_COLORS)],
                      edgecolor='none')
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                        f'{h:.1f}%', ha='center', va='bottom', fontsize=5.5)

    ax.set_xticks(x)
    ax.set_xticklabels(race_labels, fontsize=7)
    ax.set_title('Population Demographics by Race/Ethnicity', fontsize=9,
                 fontweight='bold', pad=8)
    ax.legend(fontsize=6, loc='upper right', framealpha=0.9)
    all_vals = [v for p in periods_to_plot for v in avg_data[p] if v > 0]
    if all_vals:
        ax.set_ylim(0, max(all_vals) * 1.15)
    # Clean chart: no gridlines, no Y-axis, no tick marks — data labels on bars suffice
    ax.grid(False)
    ax.spines['left'].set_visible(False)
    ax.yaxis.set_visible(False)
    ax.spines['bottom'].set_color('#cccccc')
    ax.tick_params(axis='x', length=0)
    ax.tick_params(axis='y', length=0)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Mini: Origination trend line
# ---------------------------------------------------------------------------
def render_trend_line_chart(data):
    """
    Render a compact origination trend line chart.
    data: dict like {'demographic_overview': DataFrame/list} or list of dicts with 'Metric' and year cols.
    Returns BytesIO PNG buffer.
    """
    if not data:
        return None

    # Extract Total Loans row
    rows = data if isinstance(data, list) else []
    if hasattr(data, 'to_dict'):
        rows = data.to_dict('records')

    total_row = None
    for row in rows:
        if 'total' in str(row.get('Metric', '')).lower():
            total_row = row
            break
    if not total_row:
        return None

    # Extract year columns and values
    years = []
    values = []
    for k, v in total_row.items():
        if k == 'Metric':
            continue
        try:
            yr = int(str(k).strip())
            if 2000 <= yr <= 2030:
                val = float(str(v).replace(',', '')) if v else 0
                years.append(yr)
                values.append(val)
        except (ValueError, TypeError):
            pass

    if len(years) < 2:
        return None

    # Sort by year
    paired = sorted(zip(years, values))
    years, values = zip(*paired)

    fig, ax = plt.subplots(figsize=(3.3, 1.8), dpi=150)
    _apply_mini_style(ax, fig)

    ax.plot(years, values, color=BAR_COLOR, linewidth=2, marker='o', markersize=4, zorder=3)
    for yr, val in zip(years, values):
        label = f'{val / 1000:.1f}K' if val >= 1000 else str(int(val))
        ax.text(yr, val + max(values) * 0.04, label, ha='center', fontsize=5.5, color='#333')

    ax.set_title('Total Originations', fontsize=7, fontweight='bold', color=NAVY, pad=4)
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], fontsize=5.5)
    ax.set_ylim(0, max(values) * 1.2)
    ax.yaxis.set_visible(False)
    ax.grid(axis='y', alpha=0.2)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Mini: Gap chart (lending share vs population share)
# ---------------------------------------------------------------------------
def render_gap_chart(data):
    """
    Render lending share vs population share horizontal dot plot.
    data: list of dicts with 'Metric', 'Population Share (%)', and last year column.
    Returns BytesIO PNG buffer.
    """
    if not data:
        return None

    rows = data if isinstance(data, list) else []
    if hasattr(data, 'to_dict'):
        rows = data.to_dict('records')

    # Find population share and latest year columns
    if not rows:
        return None
    sample = rows[0]
    pop_col = None
    for k in sample.keys():
        if 'population' in str(k).lower() and 'share' in str(k).lower():
            pop_col = k
            break

    year_cols = sorted([k for k in sample.keys()
                        if k not in ('Metric', pop_col) and k.strip().isdigit()])
    if not year_cols or not pop_col:
        return None
    latest_year = year_cols[-1]

    # Filter to non-total rows with population data
    plot_data = []
    for row in rows:
        metric = str(row.get('Metric', ''))
        if 'total' in metric.lower():
            continue
        pop = row.get(pop_col, 0)
        lend = row.get(latest_year, 0)
        try:
            pop_val = float(str(pop).replace('%', '').replace(',', '')) if pop else 0
            lend_val = float(str(lend).replace('%', '').replace(',', '')) if lend else 0
        except (ValueError, TypeError):
            continue
        if pop_val > 0:
            plot_data.append((metric, pop_val, lend_val))

    if not plot_data:
        return None

    fig, ax = plt.subplots(figsize=(3.3, 2.2), dpi=150)  # 20% taller
    _apply_mini_style(ax, fig)

    labels = [d[0] for d in plot_data]
    pops = [d[1] for d in plot_data]
    lends = [d[2] for d in plot_data]
    y_pos = np.arange(len(labels))

    for i, (label, pop, lend) in enumerate(plot_data):
        gap = lend - pop
        color = GREEN if gap >= 0 else RED
        ax.barh(i, lend, height=0.5, color=color, alpha=0.3, zorder=1)
        ax.plot(pop, i, 'D', color=ORANGE, markersize=5, zorder=3,
                label='Population Share' if i == 0 else '')
        ax.plot(lend, i, 'o', color=color, markersize=5, zorder=3,
                label='Lending Share' if i == 0 else '')
        ax.text(max(lend, pop) + 1, i, f'{gap:+.1f}pp', fontsize=5,
                color=color, fontweight='bold', va='center')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=5.5)
    ax.set_title(f'Lending vs. Population Share ({latest_year})', fontsize=7,
                 fontweight='bold', color=NAVY, pad=4)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
    ax.tick_params(axis='x', labelsize=5.5)
    ax.legend(fontsize=5, loc='lower right', framealpha=0.9)
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.2)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Mini: Top lenders horizontal bars
# ---------------------------------------------------------------------------
def render_lender_bars_chart(data, top_n=8):
    """Render horizontal bar chart of top lenders by volume."""
    if not data:
        return None

    rows = data if isinstance(data, list) else []
    if hasattr(data, 'to_dict'):
        rows = data.to_dict('records')
    if not rows:
        return None

    # Sort and take top N
    rows = sorted(rows, key=lambda x: float(x.get('Total Loans', 0) or 0), reverse=True)[:top_n]

    names = [str(r.get('Lender Name', ''))[:25] for r in rows]
    totals = [float(r.get('Total Loans', 0) or 0) for r in rows]
    types = [str(r.get('Lender Type', '')) for r in rows]

    type_colors = {'Bank': NAVY, 'Credit Union': TEAL}
    colors = [type_colors.get(t, BAR_COLOR) for t in types]

    fig, ax = plt.subplots(figsize=(3.3, 2.0), dpi=150)
    _apply_mini_style(ax, fig)

    y_pos = np.arange(len(names))
    ax.barh(y_pos, totals, height=0.6, color=colors, edgecolor='none')

    for i, (name, total) in enumerate(zip(names, totals)):
        ax.text(total + max(totals) * 0.02, i, str(int(total)),
                fontsize=5, va='center', color='#333')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=5)
    ax.set_title(f'Top {top_n} Lenders by Volume', fontsize=7,
                 fontweight='bold', color=NAVY, pad=4)
    ax.invert_yaxis()
    ax.xaxis.set_visible(False)
    ax.grid(axis='x', alpha=0.2)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Mini: Income share stacked comparison
# ---------------------------------------------------------------------------
def render_income_share_chart(data):
    """Render stacked bar showing income distribution: lending vs population."""
    if not data:
        return None

    rows = data if isinstance(data, list) else []
    if hasattr(data, 'to_dict'):
        rows = data.to_dict('records')
    if not rows:
        return None

    # Find pop share col and year columns
    sample = rows[0]
    pop_col = None
    for k in sample.keys():
        if 'population' in str(k).lower() and 'share' in str(k).lower():
            pop_col = k
            break
    year_cols = sorted([k for k in sample.keys()
                        if k not in ('Metric', pop_col) and str(k).strip().isdigit()])
    if not year_cols or not pop_col:
        return None

    first_year = year_cols[0]
    last_year = year_cols[-1]

    # Extract LMI, Middle, Upper rows
    categories = {}
    for row in rows:
        metric = str(row.get('Metric', '')).lower()
        if 'low to moderate' in metric or 'lmi' in metric:
            categories['LMI'] = row
        elif 'middle' in metric and 'income' in metric:
            categories['Middle'] = row
        elif 'upper' in metric:
            categories['Upper'] = row

    if len(categories) < 2:
        return None

    def _pct(row, col):
        try:
            return float(str(row.get(col, 0)).replace('%', '').replace(',', ''))
        except (ValueError, TypeError):
            return 0

    labels = [first_year, last_year, 'Population']
    lmi_vals = [_pct(categories.get('LMI', {}), first_year),
                _pct(categories.get('LMI', {}), last_year),
                _pct(categories.get('LMI', {}), pop_col)]
    mid_vals = [_pct(categories.get('Middle', {}), first_year),
                _pct(categories.get('Middle', {}), last_year),
                _pct(categories.get('Middle', {}), pop_col)]
    upper_vals = [_pct(categories.get('Upper', {}), first_year),
                  _pct(categories.get('Upper', {}), last_year),
                  _pct(categories.get('Upper', {}), pop_col)]

    fig, ax = plt.subplots(figsize=(3.3, 1.5), dpi=150)
    _apply_mini_style(ax, fig)

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, lmi_vals, height=0.5, label='LMI', color=RED, alpha=0.7)
    ax.barh(y_pos, mid_vals, height=0.5, left=lmi_vals, label='Middle', color=ORANGE, alpha=0.7)
    lefts = [l + m for l, m in zip(lmi_vals, mid_vals)]
    ax.barh(y_pos, upper_vals, height=0.5, left=lefts, label='Upper', color=GREEN, alpha=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_title('Income Distribution: Lending vs. Population', fontsize=7,
                 fontweight='bold', color=NAVY, pad=4)
    ax.legend(fontsize=5, loc='lower right', framealpha=0.8)
    ax.set_xlim(0, 105)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
    ax.tick_params(axis='x', labelsize=5)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# HHI market concentration bar chart
# ---------------------------------------------------------------------------
def render_hhi_chart(market_concentration_data):
    """Render bar chart of HHI values with threshold lines."""
    if not market_concentration_data:
        return None

    sample = market_concentration_data[0] if market_concentration_data else {}
    year_cols = sorted([k for k in sample.keys() if k not in ('Loan Purpose', 'loan_purpose')])
    if not year_cols:
        return None

    # Use "All Loans" row if available
    all_loans_row = None
    for row in market_concentration_data:
        purpose = row.get('Loan Purpose', row.get('loan_purpose', ''))
        if 'all' in str(purpose).lower():
            all_loans_row = row
            break
    if all_loans_row is None:
        all_loans_row = market_concentration_data[0]

    values = []
    for yr in year_cols:
        v = all_loans_row.get(yr, 0)
        try:
            values.append(float(v) if v else 0)
        except (ValueError, TypeError):
            values.append(0)

    fig, ax = plt.subplots(figsize=(5.0, 3.0), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(year_cols))
    ax.bar(x, values, color=BAR_COLOR, width=0.5, edgecolor='none')

    # Threshold lines — always show both for context
    max_val = max(values) if values else 500
    y_max = max(max_val * 1.3, 2800)
    ax.axhline(y=1500, color=HHI_MODERATE_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(year_cols) - 0.5, 1530, 'Moderate (1,500)', fontsize=7, color=HHI_MODERATE_COLOR, ha='right')
    ax.axhline(y=2500, color=HHI_HIGH_COLOR, linestyle='--', linewidth=1.0, alpha=0.7)
    ax.text(len(year_cols) - 0.5, 2530, 'Concentrated (2,500)', fontsize=7, color=HHI_HIGH_COLOR, ha='right')

    # Value labels on bars
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + max_val * 0.03, str(int(v)), ha='center', fontsize=8, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels([str(yr) for yr in year_cols], fontsize=8)
    ax.set_title('Market Concentration (HHI)', fontsize=10, fontweight='bold', color=NAVY, pad=6)
    ax.set_ylim(0, y_max)
    ax.yaxis.set_visible(False)
    ax.grid(False)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Sparkline for table cells
# ---------------------------------------------------------------------------
def render_sparkline(values, width_inches=0.9, height_inches=0.22, color='#1a8fc9',
                     is_downward=None):
    """Render a tiny sparkline as PNG BytesIO for embedding in a ReportLab table cell.

    Args:
        values: list of numeric values (one per year)
        width_inches: figure width
        height_inches: figure height
        color: line color (overridden by is_downward if provided)
        is_downward: if True, use red; if False, use blue; if None, auto-detect

    Returns:
        BytesIO containing PNG image bytes, or None if insufficient data.
    """
    if not values or len(values) < 2:
        return None

    clean = []
    for v in values:
        try:
            clean.append(float(v) if v is not None and v != '' else 0)
        except (ValueError, TypeError):
            clean.append(0)

    # Determine line color from trend direction
    if is_downward is None:
        is_downward = clean[-1] < clean[0]
    line_color = '#C62828' if is_downward else '#1a8fc9'

    fig, ax = plt.subplots(figsize=(width_inches, height_inches))
    ax.axis('off')
    ax.set_xlim(-0.2, len(clean) - 0.8)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Auto-scale Y-axis to data range (do NOT include zero)
    y_min = min(clean)
    y_max = max(clean)
    y_padding = (y_max - y_min) * 0.15 if y_max != y_min else 1.0
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    x = range(len(clean))
    ax.plot(x, clean, color=line_color, linewidth=1.2, solid_capstyle='round')
    # Light gray fill under all sparklines
    ax.fill_between(x, clean, y_min - y_padding, alpha=0.2, color='#E0E0E0')
    ax.scatter([0, len(clean) - 1], [clean[0], clean[-1]],
              color=line_color, s=6, zorder=5)

    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                pad_inches=0.01, transparent=True)
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
    w = width if width is not None else (width_inches * inch if width_inches else 6.5 * inch)
    h = height if height is not None else (height_inches * inch if height_inches else 3.0 * inch)
    return Image(buf, width=w, height=h)
