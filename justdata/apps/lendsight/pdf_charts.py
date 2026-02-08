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
# Chart color palettes (v2 spec Section 10)
# ---------------------------------------------------------------------------
CENSUS_COLORS = ['#4472C4', '#548235', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5']
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
# Census demographics grouped bar chart (v2 spec Section 10.1)
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
    BytesIO -- PNG image buffer, or None if no data.
    """
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

    # Build period labels and data
    period_data = {}  # {period_label: {race: [values across counties]}}
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
    avg_data = {}
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
    fig, ax = plt.subplots(figsize=(7.2, 3.5), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(race_labels))
    n_periods = len(periods_to_plot)
    bar_width = 0.25

    offsets = [i - (n_periods - 1) / 2 for i in range(n_periods)]

    for i, period in enumerate(periods_to_plot):
        bars = ax.bar(x + offsets[i] * bar_width, avg_data[period], bar_width,
                      label=period, color=CENSUS_COLORS[i % len(CENSUS_COLORS)],
                      edgecolor='none')
        # Value labels on bars
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                        f'{h:.1f}%', ha='center', va='bottom', fontsize=6.5)

    ax.set_xticks(x)
    ax.set_xticklabels(race_labels, fontsize=8)
    ax.set_ylabel('Population Share (%)', fontsize=8)
    ax.set_title('Population Demographics by Race/Ethnicity', fontsize=10,
                 fontweight='bold', pad=10)
    ax.legend(fontsize=7, loc='upper right', framealpha=0.9)

    # Set y-axis ceiling
    all_vals = [v for p in periods_to_plot for v in avg_data[p] if v > 0]
    if all_vals:
        ax.set_ylim(0, max(all_vals) * 1.15)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f%%'))
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# HHI market concentration bar chart (v2 spec Section 10.2)
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
    BytesIO -- PNG image buffer, or None if no data.
    """
    if not market_concentration_data:
        return None

    import numpy as np

    # Extract years and purposes
    sample = market_concentration_data[0] if market_concentration_data else {}
    year_cols = sorted([k for k in sample.keys() if k not in ('Loan Purpose', 'loan_purpose')])

    if not year_cols:
        return None

    # Try to find "All Loans" row, otherwise use first row
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

    fig, ax = plt.subplots(figsize=(6.0, 3.0), dpi=150)
    _apply_base_style(ax, fig)

    x = np.arange(len(year_cols))

    ax.bar(x, values, color=BAR_COLOR, width=0.5, edgecolor='none')

    # Threshold lines
    ax.axhline(y=1500, color=HHI_MODERATE_COLOR, linestyle='--', linewidth=1, alpha=0.8)
    ax.axhline(y=2500, color=HHI_HIGH_COLOR, linestyle='--', linewidth=1, alpha=0.8)

    # Threshold labels
    ax.text(len(year_cols) - 0.5, 1520, 'Moderate (1,500)', fontsize=7,
            color=HHI_MODERATE_COLOR, ha='right')
    ax.text(len(year_cols) - 0.5, 2520, 'High (2,500)', fontsize=7,
            color=HHI_HIGH_COLOR, ha='right')

    # Value labels on bars
    for i, v in enumerate(values):
        if v > 0:
            ax.text(i, v + 20, str(int(v)), ha='center', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels([str(yr) for yr in year_cols], fontsize=8)
    ax.set_ylabel('HHI Index', fontsize=8)
    ax.set_ylim(0, max(max(values) * 1.15, 2700) if values else 2700)
    ax.set_title('Market Concentration (HHI) by Year', fontsize=10,
                 fontweight='bold', pad=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Helper: BytesIO -> ReportLab Image
# ---------------------------------------------------------------------------
def chart_to_image(buf, width=None, height=None,
                   width_inches=None, height_inches=None):
    """
    Convert a PNG BytesIO buffer to a ReportLab Image flowable.

    Accepts either point values (width/height) or inch values (width_inches/height_inches).
    """
    if buf is None:
        return None
    buf.seek(0)

    w = width if width is not None else (width_inches * inch if width_inches else 6.5 * inch)
    h = height if height is not None else (height_inches * inch if height_inches else 3.0 * inch)

    return Image(buf, width=w, height=h)
