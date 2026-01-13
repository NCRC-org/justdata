"""
JSON serialization utilities for JustData applications.
Consolidates common patterns for handling numpy types, NaN values, and safe conversions.
"""

import json
import math
from typing import Any, Dict, List, Union
from decimal import Decimal

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def convert_numpy_types(obj: Any) -> Any:
    """
    Convert numpy types to native Python types for JSON serialization.

    Args:
        obj: Any object that might contain numpy types

    Returns:
        Object with all numpy types converted to Python natives
    """
    if not HAS_NUMPY:
        return obj

    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        # CRITICAL: JSON requires ALL keys to be strings
        result = {}
        for key, value in obj.items():
            key_str = str(int(key)) if isinstance(key, (int, np.integer)) else str(key)
            result[key_str] = convert_numpy_types(value)
        return result
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj


def clean_nan_values(obj: Any, replacement: Any = None) -> Any:
    """
    Recursively clean NaN and infinity values from nested data structures.

    Args:
        obj: Any object that might contain NaN values
        replacement: Value to replace NaN/inf with (default: None)

    Returns:
        Object with NaN/inf values replaced
    """
    if obj is None:
        return replacement

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return replacement
        return obj

    if HAS_NUMPY and isinstance(obj, (np.floating, np.integer)):
        if isinstance(obj, np.floating) and (np.isnan(obj) or np.isinf(obj)):
            return replacement
        return convert_numpy_types(obj)

    if HAS_PANDAS and pd.isna(obj):
        return replacement

    if isinstance(obj, dict):
        return {k: clean_nan_values(v, replacement) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [clean_nan_values(item, replacement) for item in obj]

    return obj


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int, handling pd.NA, None, and invalid values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default
    """
    if value is None:
        return default

    if HAS_PANDAS and pd.isna(value):
        return default

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float, handling pd.NA, None, and invalid values.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    if value is None:
        return default

    if HAS_PANDAS and pd.isna(value):
        return default

    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def ensure_json_serializable(obj: Any) -> Any:
    """
    Ensure an object is fully JSON serializable.
    Combines type conversion and NaN cleaning.

    Args:
        obj: Any object to make JSON serializable

    Returns:
        JSON-serializable object
    """
    # First convert numpy types
    obj = convert_numpy_types(obj)
    # Then clean NaN values
    obj = clean_nan_values(obj)
    return obj


def serialize_dataframe(df) -> List[Dict[str, Any]]:
    """
    Serialize a pandas DataFrame to a list of dictionaries,
    ensuring all values are JSON serializable.

    Args:
        df: Pandas DataFrame

    Returns:
        List of dictionaries with JSON-safe values
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required for serialize_dataframe")

    # Convert to records and clean
    records = df.to_dict(orient='records')
    return ensure_json_serializable(records)


def serialize_dataframes(dataframes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a dictionary of DataFrames to JSON-safe format.

    Args:
        dataframes: Dictionary where values may be DataFrames

    Returns:
        Dictionary with all DataFrames converted to lists of dicts
    """
    result = {}
    for key, value in dataframes.items():
        if HAS_PANDAS and isinstance(value, pd.DataFrame):
            result[key] = serialize_dataframe(value)
        else:
            result[key] = ensure_json_serializable(value)
    return result


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types, Decimal, and other special types."""

    def default(self, obj):
        if HAS_NUMPY:
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.bool_):
                return bool(obj)

        if HAS_PANDAS:
            if pd.isna(obj):
                return None
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()

        if isinstance(obj, Decimal):
            return float(obj)

        if hasattr(obj, 'isoformat'):
            return obj.isoformat()

        return super().default(obj)


def dumps(obj: Any, **kwargs) -> str:
    """
    JSON dumps with automatic handling of numpy/pandas types.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments passed to json.dumps

    Returns:
        JSON string
    """
    return json.dumps(obj, cls=JSONEncoder, **kwargs)


def loads(s: str, **kwargs) -> Any:
    """
    JSON loads (passthrough for consistency).

    Args:
        s: JSON string to parse
        **kwargs: Additional arguments passed to json.loads

    Returns:
        Parsed object
    """
    return json.loads(s, **kwargs)
