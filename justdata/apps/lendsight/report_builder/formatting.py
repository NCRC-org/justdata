"""Formatting helpers shared across mortgage report sections.

Includes Excel-safe sheet name handling, lender-name abbreviation /
capitalization, lender-type normalization, and the data cleanup pass
that's run once at the start of build_mortgage_report.
"""
import re

import pandas as pd

from justdata.shared.utils.name_utils import strip_trailing_punctuation


def sanitize_sheet_name(name: str, max_length: int = 31) -> str:
    """
    Sanitize Excel sheet name by removing invalid characters.

    Excel sheet names cannot contain: : \\ / ? * [ ]
    Also truncate to max_length (Excel limit is 31 characters).

    Args:
        name: Original sheet name
        max_length: Maximum length (default 31, Excel's limit)

    Returns:
        Sanitized sheet name
    """
    if not name:
        return 'Sheet'

    # Replace invalid characters with dash
    invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
    sanitized = name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '-')

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def abbreviate_long_lender_name(name: str, max_length: int = 30) -> str:
    """
    Abbreviate lender names that exceed max_length characters.

    Applies common word abbreviations first, then truncates if still too long.
    Preserves important parts of the name (usually the beginning).

    Args:
        name: Lender name to abbreviate
        max_length: Maximum allowed length (default 30)

    Returns:
        Abbreviated name if original was too long, otherwise original name
    """
    if not name or pd.isna(name):
        return name

    name = str(name).strip()

    # If already short enough, return as-is
    if len(name) <= max_length:
        return name

    # Common word abbreviations (case-insensitive)
    # Format: (full_word, abbreviation)
    abbreviations = [
        ('MORTGAGE', 'MTG'),
        ('GROUP', 'GRP'),
        ('CORPORATION', 'CORP'),
        ('COMPANY', 'CO'),
        ('INCORPORATED', 'INC'),
        ('ASSOCIATES', 'ASSOC'),
        ('ASSOCIATION', 'ASSOC'),
        ('FINANCIAL', 'FINL'),
        ('SERVICES', 'SVCS'),
        ('SERVICE', 'SVC'),
        ('BANKING', 'BKG'),
        ('CREDIT', 'CR'),
        ('FEDERAL', 'FED'),
        ('NATIONAL', 'NATL'),
        ('INTERNATIONAL', 'INTL'),
        ('AMERICA', 'AMER'),
        ('AMERICAN', 'AMER'),
        ('MANAGEMENT', 'MGMT'),
        ('INVESTMENT', 'INV'),
        ('INVESTMENTS', 'INV'),
        ('HOLDINGS', 'HLDGS'),
        ('HOLDING', 'HLDG'),
        ('ENTERPRISES', 'ENT'),
        ('ENTERPRISE', 'ENT'),
    ]

    # Apply abbreviations (case-insensitive)
    abbreviated = name
    for full_word, abbrev in abbreviations:
        # Use word boundaries to avoid partial matches
        pattern = re.compile(r'\b' + re.escape(full_word) + r'\b', re.IGNORECASE)
        abbreviated = pattern.sub(abbrev, abbreviated)

    # If abbreviations helped, check length again
    if len(abbreviated) <= max_length:
        return abbreviated

    # Still too long - intelligently truncate
    # Strategy: Keep the beginning, remove middle words if needed, keep important ending words
    words = abbreviated.split()

    # If we have words, try to keep first part and last word
    if len(words) > 1:
        # Keep first word(s) and last word, remove middle words
        first_word = words[0]
        last_word = words[-1]

        # Try: First word + Last word
        candidate = f"{first_word} {last_word}"
        if len(candidate) <= max_length:
            return candidate

        # Try: First word only (if it's not too long)
        if len(first_word) <= max_length:
            return first_word

        # Last resort: Truncate first word
        if len(first_word) > max_length - 4:
            return first_word[:max_length - 3] + "..."

    # Fallback: Simple truncation with ellipsis
    if len(abbreviated) > max_length:
        return abbreviated[:max_length - 3] + "..."

    return abbreviated


def correct_lender_name_capitalization(name: str) -> str:
    """
    Correct capitalization for common lender names to match their official branding.

    This function preserves the exact capitalization from the database but can apply
    corrections for well-known lenders whose names may be incorrectly capitalized in the source data.
    """
    if not name or pd.isna(name):
        return name

    name = str(name).strip()

    # Dictionary of common lender name corrections
    # Key is case-insensitive, value is the correct capitalization
    lender_corrections = {
        'jpmorgan chase': 'JPMorgan Chase',
        'jp morgan chase': 'JPMorgan Chase',
        'j.p. morgan chase': 'JPMorgan Chase',
        'j.p.morgan chase': 'JPMorgan Chase',
        'bank of america': 'Bank of America',
        'wells fargo': 'Wells Fargo',
        'citibank': 'Citibank',
        'us bank': 'U.S. Bank',
        'usbank': 'U.S. Bank',
        'pnc bank': 'PNC Bank',
        'truist': 'Truist',
        'capital one': 'Capital One',
        'first national bank': 'First National Bank',
        'huntington bank': 'Huntington Bank',
        'keybank': 'KeyBank',
        'regions bank': 'Regions Bank',
        'td bank': 'TD Bank',
        'suntrust': 'SunTrust',
        'bb&t': 'BB&T',
        'bbt': 'BB&T',
    }

    # Check for exact match (case-insensitive)
    name_lower = name.lower()
    if name_lower in lender_corrections:
        return lender_corrections[name_lower]

    # Check for partial matches (e.g., "JPMorgan Chase Bank" should match "JPMorgan Chase")
    for incorrect, correct in lender_corrections.items():
        if name_lower.startswith(incorrect) or incorrect in name_lower:
            # Replace the incorrect portion with the correct capitalization
            # Use case-insensitive replacement
            pattern = re.compile(re.escape(incorrect), re.IGNORECASE)
            corrected = pattern.sub(correct, name)
            # If the replacement changed something, return it
            if corrected != name:
                return corrected

    # If no correction found, return original name (preserving database capitalization)
    return name


def clean_mortgage_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and prepare mortgage data for analysis.

    Similar to branch data cleaning but for mortgage-specific fields.
    """
    # Make a copy to avoid modifying original
    df = df.copy()

    # Ensure numeric columns are properly typed
    numeric_columns = ['total_originations', 'lmib_originations', 'lmict_originations',
                      'mmct_originations', 'total_loan_amount', 'avg_loan_amount', 'avg_income']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Ensure year is integer
    if 'year' in df.columns:
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')

    # Fill missing lender names, convert to uppercase, and abbreviate long names
    if 'lender_name' in df.columns:
        df['lender_name'] = df['lender_name'].fillna('Unknown Lender')
        # Convert all lender names to uppercase for display
        df['lender_name'] = df['lender_name'].apply(lambda x: str(x).upper() if x else x)
        # Strip trailing commas/periods from FFIEC source data
        df['lender_name'] = df['lender_name'].apply(strip_trailing_punctuation)
        # Abbreviate names longer than 30 characters
        df['lender_name'] = df['lender_name'].apply(lambda x: abbreviate_long_lender_name(x, max_length=30) if x else x)

    return df


def map_lender_type(lender_type: str) -> str:
    """
    Map lender type from lenders18 table to simplified display name.

    Args:
        lender_type: Original lender type from lenders18.type_name

    Returns:
        Simplified lender type: 'Bank', 'Mortgage', or 'Credit Union'
    """
    if not lender_type:
        return ''

    lender_type_lower = str(lender_type).lower()

    if 'bank' in lender_type_lower or 'affiliate' in lender_type_lower:
        return 'Bank'
    elif 'mortgage' in lender_type_lower:
        return 'Mortgage'
    elif 'credit union' in lender_type_lower or 'credit' in lender_type_lower:
        return 'Credit Union'
    else:
        return lender_type  # Return original if no match
