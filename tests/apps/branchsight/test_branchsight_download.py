"""BranchSight /download works from a result read back from the analysis
cache, where tables are lists of records (every download failed on those)."""

import io
import zipfile

import pytest
from openpyxl import load_workbook

YEARS = [2021, 2022, 2023, 2024, 2025]
RESULT = {
    "metadata": {"counties": ["Lowndes County, Alabama"], "years": YEARS},
    "ai_insights": {"key_findings": "Text.", "table_narratives": {}},
    "report_data": {
        "summary": [{"Variable": "Total Branches", **{str(y): 4 for y in YEARS}, "Net Change": -1}],
        "by_bank": [{"Bank Name": "FIRST CITIZENS BANK", "Total Branches": 2, "Deposits ($ Millions)": 74.6,
                     "LMI Only Branches": 0, "MMCT Only Branches": 0, "Both LMICT/MMCT Branches": 2, "Net Change": 0}],
        "by_county": [], "trends": [],
        "raw_data": [{"bank_name": "FIRST CITIZENS BANK", "year": "2025", "uninumbr": "1", "lmict": 1, "mmct": 1}],
        "hhi": {"hhi": 5487.76, "year": 2025}, "hhi_by_year": [{"year": 2025, "hhi_value": 5487.76}],
    },
}


@pytest.fixture
def client(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.branchsight.blueprint as bp
    import justdata.apps.branchsight.pdf_report as pdf
    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", lambda job_id: RESULT)
    monkeypatch.setattr(pdf, "generate_branchsight_pdf", lambda *a: io.BytesIO(b"%PDF-1.4"))
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def test_excel_from_cached_lists_names_the_county(client):
    resp = client.get("/branchsight/download?format=excel&job_id=x")
    assert resp.status_code == 200, resp.get_json()
    assert "Lowndes_County_Alabama" in resp.headers["Content-Disposition"]
    wb = load_workbook(io.BytesIO(resp.data))
    assert {"Section 1- Yearly Breakdown", "Section 2- Analysis by Bank", "Raw Data"} <= set(wb.sheetnames)
    methods = {r[0]: r[1] for r in wb["Methods & Definitions"].iter_rows(values_only=True)}
    assert "BankFind" not in methods["Data Source"]
    assert "excludes" not in methods["Branch Count"]
    assert "FDIC Certificate Number" not in methods


def test_zip_and_csv_from_cached_lists(client):
    names = zipfile.ZipFile(io.BytesIO(client.get("/branchsight/download?format=zip&job_id=x").data)).namelist()
    assert any(n.endswith(".xlsx") for n in names) and any(n.endswith(".pdf") for n in names)
    csv = client.get("/branchsight/download?format=csv&job_id=x")
    assert csv.status_code == 200 and b"Total Branches" in csv.data


def test_export_error_shows_a_reference_not_exception_text(client, monkeypatch):
    import justdata.apps.branchsight.pdf_report as pdf
    def boom(*a):
        raise RuntimeError("secret path /tmp/x")
    monkeypatch.setattr(pdf, "generate_branchsight_pdf", boom)
    err = client.get("/branchsight/download?format=pdf&job_id=x").get_json()["error"]
    assert "secret" not in err and "Reference:" in err
