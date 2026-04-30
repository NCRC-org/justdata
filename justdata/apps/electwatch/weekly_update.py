"""Entry point for the ElectWatch weekly data pipeline.

This module is imported by Dockerfile.electwatch-job:
    from justdata.apps.electwatch.weekly_update import WeeklyDataUpdate

The pipeline implementation lives in justdata/apps/electwatch/pipeline/.
"""
from justdata.apps.electwatch.pipeline.coordinator import WeeklyDataUpdate, main

__all__ = ["WeeklyDataUpdate", "main"]
