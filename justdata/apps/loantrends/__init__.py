"""
LoanTrends - National HMDA quarterly trends analysis application.
Uses CFPB Quarterly Data Graph API to analyze national mortgage lending trends.
"""

# Import version from version.py for consistency
try:
    from justdata.apps.loantrends.version import __version__
except ImportError:
    __version__ = "0.9.0"  # Fallback




