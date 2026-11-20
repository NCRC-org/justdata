"""Exports show when the analysis ran, in ET (triage T3; QA LS-058, X-012, BZ-030)."""
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from justdata.shared.utils.report_time import analysis_date, analysis_stamp, analysis_time, et_stamp, et_time

ROOT = Path(__file__).resolve().parents[2] / "justdata"


def test_et_formatting_follows_ncrc_style():
    assert et_stamp(datetime(2026, 11, 17, 19, 5, tzinfo=timezone.utc)) == "Nov. 17, 2026, 2:05 pm ET"
    assert et_time(datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc)) == "9 am ET"
    assert et_time(datetime(2026, 11, 17, 17, 0, tzinfo=timezone.utc)) == "noon ET"
    assert et_time(datetime(2026, 11, 18, 5, 0, tzinfo=timezone.utc)) == "midnight ET"
    # Daylight time: 13:30 UTC in July is 9:30 am ET.
    assert et_stamp(datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc)) == "July 2, 2026, 9:30 am ET"
    assert et_stamp(datetime(2026, 9, 3, 16, 0, tzinfo=timezone.utc)) == "Sept. 3, 2026, noon ET"


def test_stored_time_is_read_and_a_naive_value_is_utc():
    meta = {"generated_at": "2026-11-17T19:05:00"}          # datetime.now().isoformat() on Cloud Run
    assert analysis_stamp(meta) == "Nov. 17, 2026, 2:05 pm ET"
    assert analysis_date({"created_at": "2026-11-18T03:00:00+00:00"}) == "Nov. 17, 2026"   # still the 17th in ET


def test_missing_time_falls_back_to_now():
    before = datetime.now(timezone.utc)
    assert analysis_time({"generated_at": ""}) >= before
    assert analysis_time(None) >= before


def test_lendsight_excel_stamps_the_analysis_time(tmp_path):
    from openpyxl import load_workbook
    from justdata.apps.lendsight.report_builder.excel_export.writer import save_mortgage_excel_report
    out = tmp_path / "ls.xlsx"
    save_mortgage_excel_report({"raw_data": pd.DataFrame()}, str(out),
                               {"years": [2024, 2025], "counties": ["Loving County, Texas"],
                                "generated_at": "2026-11-17T19:05:00"})
    text = " ".join(str(v) for ws in load_workbook(out).worksheets
                    for row in ws.iter_rows(values_only=True) for v in row if v)
    assert "Generated: Nov. 17, 2026, 2:05 pm ET" in text


def test_no_sight_export_stamps_the_download_time():
    files = ["apps/lendsight/pdf_report.py", "apps/lendsight/report_builder/excel_export/writer.py",
             "apps/bizsight/pdf_report.py", "apps/bizsight/excel_export.py",
             "apps/branchsight/pdf_report.py", "apps/branchsight/blueprint.py",
             "shared/pdf/base_report.py", "shared/reporting/report_builder.py"]
    for rel in files:
        text = (ROOT / rel).read_text()
        # Download file names may still carry the download time; content may not.
        assert not re.search(r"gen_date = datetime\.now\(\)", text), rel
        assert not re.search(r"Generated[^\n]*datetime\.now\(\)\.strftime", text), rel


def test_download_file_names_label_the_time_as_et():
    from justdata.shared.utils.report_time import download_stamp
    assert re.fullmatch(r"\d{8}_\d{6}_ET", download_stamp())
    for rel in ["apps/lendsight/blueprint.py", "apps/bizsight/blueprint.py",
                "apps/bizsight/excel_export.py", "apps/branchsight/blueprint.py"]:
        assert "%Y%m%d_%H%M%S" not in (ROOT / rel).read_text(), rel
