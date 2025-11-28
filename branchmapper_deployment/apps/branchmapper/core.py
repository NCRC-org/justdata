#!/usr/bin/env python3
"""
BranchMapper core utilities for loading SQL templates.
"""

import os


def load_sql_template() -> str:
    """Load the SQL template for branch queries."""
    sql_template_path = os.path.join(
        os.path.dirname(__file__),
        'sql_templates',
        'branch_report.sql'
    )
    try:
        with open(sql_template_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise Exception(f"SQL template not found at {sql_template_path}")

