"""Lenderprofile data collector package.

Public API:
    DataCollector  -- orchestrates fetches from FDIC / GLEIF / SEC / CFPB /
                      HMDA / News / Federal Register / Federal Reserve /
                      Regulations.gov / CourtListener / Seeking Alpha and
                      assembles a complete institution profile.
"""
from justdata.apps.lenderprofile.processors.collector.core import DataCollector

__all__ = ["DataCollector"]
