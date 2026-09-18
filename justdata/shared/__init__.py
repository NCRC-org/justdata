# JustData Shared Infrastructure
# This module provides shared utilities across all JustData applications

# Core infrastructure
# The Flask app factory is imported directly from justdata.shared.web.app_factory
# by the apps that use it; it is deliberately not re-exported here.
from justdata.shared.core.config import BaseAppConfig, get_settings

# Utilities
from justdata.shared.utils.json_utils import (
    convert_numpy_types,
    clean_nan_values,
    safe_int,
    safe_float,
    ensure_json_serializable,
    serialize_dataframes
)

__all__ = [
    # Core
    'BaseAppConfig',
    'get_settings',
    # JSON utilities
    'convert_numpy_types',
    'clean_nan_values',
    'safe_int',
    'safe_float',
    'ensure_json_serializable',
    'serialize_dataframes',
]
