"""Users never see raw exception text (hygiene PR, item 5)."""

import re

from justdata.shared.utils.error_ref import GENERIC_ERROR, user_error


def test_user_error_hides_the_exception_and_logs_it(capsys):
    try:
        raise RuntimeError("bigquery: table justdata-ncrc.secret.x not found")
    except RuntimeError as e:
        text, ref = user_error(exc=e, context="test")
    assert text == f"{GENERIC_ERROR} Reference: {ref}"
    assert re.fullmatch(r"[0-9a-f]{8}", ref)
    assert "secret" not in text
    logged = capsys.readouterr().out
    assert f"ref={ref}" in logged and "RuntimeError" in logged and "secret.x" in logged


def test_bizsight_analysis_exception_is_not_shown(monkeypatch):
    import justdata.apps.bizsight.core as core

    class Boom(Exception):
        pass

    def explode(*a, **k):
        raise Boom("Query error: 400 Unrecognized name: raw_column at [3:5]")

    monkeypatch.setattr(core, "parse_web_parameters", explode, raising=False)
    monkeypatch.setattr(core, "BigQueryClient", explode, raising=False)
    result = core.run_analysis({"geoid5": "01085", "name": "Lowndes County, Alabama"}, "2020,2021,2022,2023,2024",
                               "test-job", None)
    assert result["success"] is False
    assert "Unrecognized name" not in result["error"] and "raw_column" not in result["error"]
    assert re.search(r"Reference: [0-9a-f]{8}$", result["error"])
