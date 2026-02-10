# ElectWatch Session Notes

**Last Updated:** 2026-01-20

## Recent Changes (January 20, 2026)

### Leaderboard Redesign

The ElectWatch leaderboard was completely redesigned with new columns and features:

#### New Columns
1. **#** - Rank based on involvement score
2. **Official** - Name, photo, party indicator, state/district
3. **Trend** - Two indicators:
   - Finance % trend: ▲ (increasing), ▼ (decreasing), ► (stable)
   - Stock activity: ◆ (net buyer), ◇ (net seller)
4. **Total $** - All contributions (PAC + Individual combined)
5. **Finance $** - Finance/housing sector contributions only
6. **Finance %** - Percentage from finance sector (color-coded: red ≥50%, orange ≥25%)
7. **Buys** - Stock purchases in finance/housing companies
8. **Sells** - Stock sales in finance/housing companies
9. **Top Donors** - Company names (merged from PAC + individual contributions)

#### Key Files Modified
- `justdata/apps/electwatch/templates/electwatch_dashboard.html` - New column structure, Tippy.js tooltips, trend/donor CSS
- `justdata/apps/electwatch/weekly_update.py` - New scoring formula, `_build_top_donors()` method
- `justdata/apps/electwatch/services/data_store.py` - Trend snapshot storage, `enrich_officials_with_trends()`
- `justdata/apps/electwatch/services/mapping_store.py` - New file for admin mappings, unmatched entity detection
- `justdata/apps/electwatch/blueprint.py` - New API endpoints for unmatched PACs/tickers

### Scoring Formula Update

**Old formula:** `contrib_score = contributions / 1000`

**New formula:** `contrib_score = (total_contributions / 1000) * finance_pct`

This weights contribution scores by the percentage coming from finance/housing sector, surfacing officials who are heavily reliant on financial industry money.

### Top Donors Feature

The `top_donors` field is built by:
1. Collecting PAC contributions from `top_financial_pacs`
2. Collecting individual contributions from `individual_financial_by_employer`
3. Normalizing company names (e.g., "JPMORGAN CHASE & CO PAC" → "JPMorgan Chase")
4. Merging by canonical company name
5. Detecting stock trade overlap (flags when official receives contributions from AND trades stock in same company)

### Trend Tracking

Quarterly snapshots are now stored to track changes over time:
- `save_trend_snapshot()` - Saves current finance_pct for each official
- `get_trend_history()` - Retrieves historical snapshots
- `enrich_officials_with_trends()` - Adds trend direction, arrows, stock activity indicators
- Stores up to 104 weeks (2 years) of history

### Admin Features

New "Unmatched Entities" tab in the admin panel showing:
- PAC names that couldn't be mapped to known companies
- Employer names that couldn't be matched to firms
- Stock tickers that aren't categorized into industries

### Data Structure

Each official now has:
```python
{
    'contributions_display': {
        'total': 123456,           # PAC + Individual total
        'financial': 45678,        # Finance sector total
        'financial_pct': 37.0,     # Percentage
        'pac_total': 100000,
        'pac_financial': 30000,
        'individual_total': 23456,
        'individual_financial': 15678
    },
    'top_donors': [
        {
            'name': 'JPMorgan Chase',
            'pac_amount': 5000,
            'individual_amount': 3000,
            'total': 8000,
            'stock_overlap': True  # Also trades their stock
        }
    ],
    'finance_trend_direction': 'increasing',  # or 'decreasing', 'stable'
    'finance_trend_arrow': '▲',
    'finance_pct_change': 5.2,
    'stock_trend_direction': 'buyer',  # or 'seller', 'neutral'
    'stock_trend_icon': '◆'
}
```

### Deployment

- **Commit:** `7b6844a`
- **Branch:** `Jason_TestApps`
- **Cloud Run Service:** `justdata-test`
- **URL:** https://justdata-test-892833260112.us-east1.run.app
- **ElectWatch:** https://justdata-test-892833260112.us-east1.run.app/electwatch/

### User Authentication

Firebase-based authentication system was also deployed:
- `justdata/main/auth.py` - Authentication logic
- `justdata/shared/web/static/js/auth.js` - Frontend auth handling
- `justdata/shared/web/templates/base_app.html` - Auth UI integration

---

## Company Name Mappings

Key PAC-to-company normalizations in `_build_top_donors()`:
- JPMORGAN CHASE, JP MORGAN → JPMorgan Chase
- BANK OF AMERICA, BOFA → Bank of America
- GOLDMAN SACHS → Goldman Sachs
- WELLS FARGO → Wells Fargo
- CITIGROUP, CITI → Citigroup
- etc.

Ticker-to-company mappings for overlap detection:
- JPM → JPMorgan Chase
- BAC → Bank of America
- GS → Goldman Sachs
- etc.

---

## Weekly Update Process

The weekly update (`weekly_update.py`) now:
1. Fetches Congress members from congress.gov API
2. Fetches stock trades from Financial Modeling Prep
3. Enriches with FEC candidate data
4. Fetches financial sector PAC contributions (Schedule A)
5. Fetches individual financial sector contributions
6. Computes involvement scores with new formula
7. Builds `top_donors` with overlap detection
8. Saves trend snapshot
9. Enriches officials with trend data
10. Generates AI insights
11. Saves all data to weekly snapshot and current directory
