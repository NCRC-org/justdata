#!/usr/bin/env python3
"""
MergerMeter data utilities for getting last 5 years dynamically.
"""

from justdata.shared.utils.bigquery_client import get_bigquery_client
from typing import List
from .config import PROJECT_ID

# App name for per-app credential support
APP_NAME = 'MERGERMETER'


def get_last_5_years_hmda() -> List[int]:
    """
    Get the last 5 years dynamically from HMDA data (hmda.hmda).
    
    Returns:
        List of the 5 most recent years available, sorted descending (e.g., [2024, 2023, 2022, 2021, 2020])
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = f"""
        SELECT DISTINCT CAST(activity_year AS INT64) as year
        FROM `{PROJECT_ID}.hmda.hmda`
        WHERE activity_year IS NOT NULL
        ORDER BY year DESC
        LIMIT 5
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [int(row.year) for row in results]
        if years:
            print(f"✅ Fetched last 5 HMDA years: {years}")
            return years
        else:
            # Fallback to recent years
            print("⚠️  No HMDA years found, using fallback")
            return list(range(2020, 2025))  # 2020-2024
    except Exception as e:
        print(f"Error fetching HMDA years: {e}")
        # Fallback to recent years
        return list(range(2020, 2025))  # 2020-2024


def get_last_5_years_sb() -> List[int]:
    """
    Get the last 5 years dynamically from SB disclosure data (sb.disclosure).
    
    Returns:
        List of the 5 most recent years available, sorted descending (e.g., [2024, 2023, 2022, 2021, 2020])
    """
    try:
        client = get_bigquery_client(PROJECT_ID, app_name=APP_NAME)
        query = f"""
        SELECT DISTINCT year
        FROM `{PROJECT_ID}.sb.disclosure`
        WHERE year IS NOT NULL
        ORDER BY year DESC
        LIMIT 5
        """
        query_job = client.query(query)
        results = query_job.result()
        years = [int(row.year) for row in results]
        if years:
            print(f"✅ Fetched last 5 SB disclosure years: {years}")
            return years
        else:
            # Fallback to recent years
            print("⚠️  No SB disclosure years found, using fallback")
            return list(range(2020, 2025))  # 2020-2024
    except Exception as e:
        print(f"Error fetching SB disclosure years: {e}")
        # Fallback to recent years
        return list(range(2020, 2025))  # 2020-2024

