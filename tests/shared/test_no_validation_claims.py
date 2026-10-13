"""Jad, 2026-10-13: the three data-validation sentences are removed, for the
same reason as the earlier quality-assurance claims (nothing on the page
backs them)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "justdata/apps/bizsight/templates/partials/bizsight_methods.html",
    "justdata/apps/bizsight/excel_export.py",
    "justdata/apps/branchsight/templates/partials/branchsight_methods.html",
]
CLAIMS = [
    "Income tract classifications are validated",
    "tested by NCRC Research staff",
    "validated by NCRC Research staff",
]


def test_validation_sentences_are_gone():
    for f in FILES:
        text = (ROOT / f).read_text()
        for claim in CLAIMS:
            assert claim not in text, (f, claim)
