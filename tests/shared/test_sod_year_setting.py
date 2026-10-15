"""The FDIC Summary of Deposits year is one setting (shared/core/sod_years.py).

No app code types an SOD year in: not as a ``year`` argument or default, not in
a request default, an API URL, a SQL year filter or an on-page label. And every
SOD query that filters by year reads branchsight.sod and sod_legacy together,
so a year stays readable when the yearly load moves it into sod_legacy.
"""
import re
from pathlib import Path

import pytest

from justdata.shared.core import sod_years

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'justdata'

# Every file that reads SOD (or the one-year census table) or shows its year.
SOD_READERS = sorted(
    [p for d in ('apps/mergermeter', 'apps/branchsight', 'apps/branchmapper')
     for p in (APP / d).rglob('*') if p.suffix in ('.py', '.sql', '.html', '.js')]
    + [APP / f for f in (
        'apps/dataexplorer/config.py',
        'apps/dataexplorer/data_utils.py',
        'apps/dataexplorer/lender_analysis/core.py',
        'apps/dotlender/data/queries.py',
        'apps/dotlender/sql_templates/tract_race_shares.sql',
        'shared/reporting/excel/worksheets/notes.py',
        'shared/web/static/js/mergermeter/mm_areas.js',
        'main/landing_content.py',
        'main/launcher_content.py',
    )]
)

YEAR = r"20[0-9]{2}"
TYPED_IN = [
    ('year argument or default', re.compile(rf"\byear\s*(:\s*int\s*)?=\s*['\"]?{YEAR}\b")),
    ('request default', re.compile(rf"get\(\s*['\"]year['\"]\s*,\s*['\"]?{YEAR}")),
    ('SQL year filter', re.compile(rf"\byear\b[^\n]{{0,30}}=\s*['\"]{YEAR}['\"]")),
    ('SOD label', re.compile(rf"(Summary of Deposits|\bSOD)\W{{0,4}}(\(|June 30, )?{YEAR}")),
    ('June 30 date', re.compile(rf"June 30, {YEAR}|['\"`]{YEAR}-06-30")),
    ('branch data year', re.compile(rf"Branch Data Year: {YEAR}|Year: {YEAR} \(most recent")),
]


def _hits(path):
    text = path.read_text(encoding='utf-8')
    for n, line in enumerate(text.splitlines(), 1):
        for what, pattern in TYPED_IN:
            if pattern.search(line):
                yield f'{path.relative_to(ROOT)}:{n}: {what}: {line.strip()[:120]}'


def test_reader_list_exists():
    missing = [str(p) for p in SOD_READERS if not p.exists()]
    assert not missing, missing


def test_patterns_catch_the_forms_an_sod_year_takes():
    samples = [
        "    year: int = 2025\n",
        "query = build_branch_query(rssd, geoids, year=2025)",
        "year = int(request.args.get('year', '2025'))",
        "WHERE CAST(b.year AS STRING) = '2025'",
        "WHERE year = '2025'",
        "`${APP_BASE_URL}/api/branches-in-bounds?${params}&year=2025`",
        "(FDIC Summary of Deposits 2025)",
        "Since Last SOD (June 30, 2025)",
        "return { start: '2025-06-30', end: today };",
        'ws.cell(row, 1, "Branch Data Year: 2025")',
    ]
    for s in samples:
        assert any(p.search(s) for _, p in TYPED_IN), s


@pytest.mark.parametrize('path', SOD_READERS, ids=lambda p: str(p.relative_to(APP)))
def test_no_typed_in_sod_year(path):
    hits = list(_hits(path))
    assert not hits, 'read the year from shared/core/sod_years.py:\n' + '\n'.join(hits)


def test_every_app_reads_the_one_setting():
    from justdata.apps.branchsight import config as branchsight_config
    from justdata.apps.dataexplorer.config import BRANCH_YEARS
    from justdata.main import landing_content, launcher_content

    latest = sod_years.SOD_LATEST_YEAR
    assert branchsight_config.SOD_LATEST_YEAR == latest
    assert branchsight_config.SOD_YEARS == sod_years.sod_analysis_years()
    assert branchsight_config.SOD_YEARS[-1] == latest
    assert len(branchsight_config.SOD_YEARS) == sod_years.SOD_ANALYSIS_SPAN
    assert BRANCH_YEARS[0] == sod_years.SOD_EARLIEST_YEAR and BRANCH_YEARS[-1] == latest
    assert landing_content.SOD_LAST_YEAR == latest
    assert launcher_content.ANALYSIS_YEARS['branchsight'].endswith(f'to {latest}')


def test_mergermeter_sod_queries_read_every_year():
    from justdata.apps.mergermeter import query_builders as q

    for build in (q.build_branch_query, q.build_branch_market_query, q.build_branch_details_query):
        sql = build('693224', ['51087'])
        assert 'branchsight.sod_legacy' in sql, build.__name__
        assert f"= '{sod_years.SOD_LATEST_YEAR}'" in sql, build.__name__
    for name in ('mergermeter_all_branches_for_bank.sql', 'mergermeter_cbsa_deposit_shares.sql'):
        sql = (APP / 'apps/mergermeter/sql_templates' / name).read_text()
        assert '{SOD_ALL_YEARS}' in sql and 'branchsight.sod`' not in sql, name
    hhi = (APP / 'apps/mergermeter/hhi_calculator.py').read_text()
    assert 'FROM {sod_all_years()} b' in hhi and 'branchsight.sod`' not in hhi


def test_sod_all_years_reads_both_tables():
    sql = sod_years.sod_all_years('justdata-ncrc')
    assert '`justdata-ncrc.branchsight.sod`' in sql
    assert '`justdata-ncrc.branchsight.sod_legacy`' in sql


def test_mergermeter_cache_key_carries_the_sod_year():
    src = (APP / 'apps/mergermeter/blueprint.py').read_text()
    assert "cache_params['sod_year'] = str(SOD_LATEST_YEAR)" in src


def test_dotlender_reads_the_latest_census_year():
    sql = (APP / 'apps/dotlender/sql_templates/tract_race_shares.sql').read_text()
    assert 'WHERE year = (SELECT MAX(year) FROM `justdata-ncrc.shared.census`)' in sql
