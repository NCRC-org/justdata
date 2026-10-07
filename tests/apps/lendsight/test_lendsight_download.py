"""LendSight /download: "excel" is the workbook alone, "zip" the bundle."""

import io
import zipfile

import pytest


@pytest.fixture
def client(monkeypatch):
    from justdata.main.app import create_app
    import justdata.apps.lendsight.blueprint as bp
    import justdata.apps.lendsight.report_builder as rb
    import justdata.apps.lendsight.pdf_report as pdf

    monkeypatch.setattr(bp, "get_analysis_result_by_job_id", lambda job_id: {
        "report_data": {"demographic_overview": [{"Metric": "Total Loans"}]},
        "metadata": {"counties": ["Cook County, Illinois"], "years": [2021, 2025]},
        "ai_insights": {},
    })
    monkeypatch.setattr(rb, "save_mortgage_excel_report",
                        lambda data, path, metadata=None: open(path, "wb").write(b"PK\x03\x04xlsx"))
    monkeypatch.setattr(pdf, "generate_lendsight_pdf", lambda *a: io.BytesIO(b"%PDF-1.4"))
    app = create_app()
    app.config["TESTING"] = True
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_type"] = "staff"
        s["firebase_user"] = {"uid": "t", "email": "t@example.org", "email_verified": True}
    return c


def test_excel_is_the_workbook_alone(client):
    resp = client.get("/lendsight/download?format=excel&job_id=x")
    assert resp.status_code == 200
    assert resp.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert resp.data == b"PK\x03\x04xlsx"
    assert ".xlsx" in resp.headers["Content-Disposition"]


def test_zip_still_bundles_workbook_and_pdf(client):
    resp = client.get("/lendsight/download?format=zip&job_id=x")
    assert resp.mimetype == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(resp.data)).namelist()
    assert any(n.endswith(".xlsx") for n in names) and any(n.endswith(".pdf") for n in names)


def test_unknown_format_names_valid_ones(client):
    resp = client.get("/lendsight/download?format=docx&job_id=x")
    assert resp.status_code == 400 and "docx" not in resp.get_data(as_text=True)
