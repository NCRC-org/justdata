# JustData Shared Infrastructure
# This module provides shared utilities across all JustData applications

# Core infrastructure
from justdata.shared.core import create_app, register_standard_routes
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
    'create_app',
    'register_standard_routes',
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
