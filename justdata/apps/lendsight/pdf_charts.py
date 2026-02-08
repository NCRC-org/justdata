"""
LendSight chart renderers for magazine-style PDF reports.

Uses matplotlib to produce print-friendly PNG images returned as BytesIO buffers.
"""

from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from reportlab.platypus import Image
from reportlab.lib.units import inch


# ---------------------------------------------------------------------------
# Muted, print-friendly color palette
# ---------------------------------------------------------------------------
CHART_COLORS = [
    '#1a8fc9',  # JustData blue
    '#2d8659',  # muted green
    '#d4783c',  # burnt orange
    '#7b5ea7',  # muted purple
    '#c94c4c',  # muted red
    '#4a7c8f',  # teal
    '#8c8c3e',  # olive
]

BAR_COLOR = '#1a8fc9'
HHI_MODERATE_COLOR = '#e8a838'
HHI_HIGH_COLOR = '#c94c4c'


def _apply_base_style(ax, fig):
    """Apply common clean styling to axes."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.5)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.tick_params(axis='both', labelsize=7, length=3, width=0.5)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')


# ---------------------------------------------------------------------------
# Census demographics grouped bar chart
# ---------------------------------------------------------------------------
def render_census_demographics_chart(census_data, counties=None):
    """
    Render a grouped bar chart showing race/ethnicity population by time period.

    Parameters
    ----------
    census_data : dict
        Nested dict: {county_name: {time_periods: {period_key: {demographics: {...}}}}}
    counties : list[str] or None
        County names to include. If None, use all.

    Returns
    -------
    BytesIO — PNG image buffer, or None if no data.
    """
    if not census_data:
        return None

    # Collect data across counties and time periods
    race_keys = [
        ('white_percentage', 'White'),
        ('black_percentage', 'Black'),
        ('hispanic_percentage', 'Hispanic'),
        ('asian_percentage', 'Asian'),
        ('native_american_percentage', 'Native American'),
        ('multi_racial_percentage', 'Multi-Racial'),
    ]

    # Build period labels and data
    period_data = {}  # {period_label: {race: avg_pct}}
    period_order = ['2010 Census', '2020 Census']  # Prefer this order

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

    # Average across counties for each period
    periods_to_plot = [p for p in period_order if p in period_data]
    if not periods_to_plot:
        return None

    race_labels = [rk[1] for rk in race_keys]
    avg_data = {}  # {period: [avg for each race]}
    for period in periods_to_plot:
        avgs = []
        for race in race_labels:
            vals = period_data[period].get(race, [])
            avgs.append(sum(vals) / len(vals) if vals else 0)
        avg_data[period] = avgs

    # Filter out races with zero across all periods
    non_zero_mask = []
    for i, race in enumerate(race_labels):
        if any(avg_data[p][i] > 0.1 for p in periods_to_plot):
            non_zero_mask.append(i)

    race_labels = [race_labels[i] for i in non_zero_mask]
    for p in periods_to_plot:
        avg_data[p] = [avg_data[p][i] for i in non_zero_mask]

    if not race_labels:
        return None

    # Plot
    import numpy as np
    fig, ax = plt.subplots(figsize=(7.0, 3.2), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(race_labels))
    n_periods = len(periods_to_plot)
    width = 0.7 / max(n_periods, 1)

    for i, period in enumerate(periods_to_plot):
        offset = (i - (n_periods - 1) / 2) * width
        bars = ax.bar(x + offset, avg_data[period], width,
                      label=period, color=CHART_COLORS[i % len(CHART_COLORS)],
                      edgecolor='white', linewidth=0.3)
        # Value labels on bars
        for bar in bars:
            h = bar.get_height()
            if h > 2:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                        f'{h:.1f}%', ha='center', va='bottom', fontsize=6)

    ax.set_xticks(x)
    ax.set_xticklabels(race_labels, fontsize=7)
    ax.set_ylabel('Population Share (%)', fontsize=7)
    ax.set_title('Population Demographics by Race/Ethnicity', fontsize=9, fontweight='bold', pad=8)
    ax.legend(fontsize=7, loc='upper right', framealpha=0.9)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# HHI market concentration bar chart
# ---------------------------------------------------------------------------
def render_hhi_chart(market_concentration_data):
    """
    Render a bar chart of HHI values with threshold lines.

    Parameters
    ----------
    market_concentration_data : list[dict]
        Each dict has 'Loan Purpose' key and year columns with HHI values.
        E.g. [{'Loan Purpose': 'Purchase', '2020': 450, '2021': 500, ...}]

    Returns
    -------
    BytesIO — PNG image buffer, or None if no data.
    """
    if not market_concentration_data:
        return None

    import numpy as np

    # Extract years and purposes
    sample = market_concentration_data[0] if market_concentration_data else {}
    year_cols = sorted([k for k in sample.keys() if k not in ('Loan Purpose', 'loan_purpose')])

    if not year_cols:
        return None

    purposes = [row.get('Loan Purpose', row.get('loan_purpose', 'Unknown'))
                for row in market_concentration_data]

    fig, ax = plt.subplots(figsize=(6.0, 3.0), dpi=150)
    _apply_base_style(ax, fig)

    n_purposes = len(purposes)
    n_years = len(year_cols)
    x = np.arange(n_years)
    width = 0.7 / max(n_purposes, 1)

    for i, row in enumerate(market_concentration_data):
        purpose = purposes[i]
        vals = []
        for yr in year_cols:
            v = row.get(yr, 0)
            try:
                vals.append(float(v) if v else 0)
            except (ValueError, TypeError):
                vals.append(0)

        offset = (i - (n_purposes - 1) / 2) * width
        color = CHART_COLORS[i % len(CHART_COLORS)]
        ax.bar(x + offset, vals, width, label=purpose, color=color,
               edgecolor='white', linewidth=0.3)

    # Threshold lines
    ax.axhline(y=1500, color=HHI_MODERATE_COLOR, linestyle='--', linewidth=1, alpha=0.8)
    ax.axhline(y=2500, color=HHI_HIGH_COLOR, linestyle='--', linewidth=1, alpha=0.8)

    # Threshold labels
    x_max = len(year_cols) - 1
    ax.text(x_max + 0.4, 1500, 'Moderate (1500)', fontsize=6,
            color=HHI_MODERATE_COLOR, va='center')
    ax.text(x_max + 0.4, 2500, 'High (2500)', fontsize=6,
            color=HHI_HIGH_COLOR, va='center')

    ax.set_xticks(x)
    ax.set_xticklabels(year_cols, fontsize=7)
    ax.set_ylabel('HHI Index', fontsize=7)
    ax.set_title('Market Concentration (HHI) by Year', fontsize=9, fontweight='bold', pad=8)
    if n_purposes > 1:
        ax.legend(fontsize=7, loc='upper left', framealpha=0.9)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Helper: BytesIO → ReportLab Image
# ---------------------------------------------------------------------------
def chart_to_image(buf, width_inches=6.5, height_inches=3.0):
    """
    Convert a PNG BytesIO buffer to a ReportLab Image flowable.

    Parameters
    ----------
    buf : BytesIO — PNG image data
    width_inches : float
    height_inches : float

    Returns
    -------
    reportlab.platypus.Image or None
    """
    if buf is None:
        return None
    buf.seek(0)
    return Image(buf, width=width_inches * inch, height=height_inches * inch)
