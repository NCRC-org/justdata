"""
JustData Analytics Application

Internal admin-only application for visualizing user activity patterns
across JustData. Shows where users are located, what geographies and
lenders they're researching, and identifies coalition-building opportunities.
"""

from .blueprint import analytics_bp

__all__ = ['analytics_bp']
