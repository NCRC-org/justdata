"""
Centralized version registry for all JustData applications.
See justdata/VERSIONING.md for update instructions.
"""

VERSIONS = {
    'platform': '0.9.0',
    'lendsight': '0.9.0',
    'branchseeker': '0.9.0',
    'branchsight': '0.9.0',
    'lenderprofile': '0.9.0',
    'bizsight': '0.9.0',
    'mergermeter': '0.9.0',
    'dataexplorer': '0.9.0',
    'branchmapper': '0.9.0',
    'electwatch': '0.9.0',
    'loantrends': '0.9.0',
    'commentmaker': '0.9.0',
    'justpolicy': '0.9.0',
    'analytics': '0.9.0',
    'memberview': '0.9.0',
}


def get_version(app_name: str) -> str:
    """Get version for a specific app."""
    return VERSIONS.get(app_name.lower(), '0.0.0')


def get_all_versions() -> dict:
    """Get all app versions."""
    return VERSIONS.copy()
