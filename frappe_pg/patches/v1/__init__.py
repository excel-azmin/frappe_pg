"""
Version 1 Patches for PostgreSQL Compatibility
==============================================

This package contains the initial set of patches for ERPNext
PostgreSQL compatibility.
"""

from .apply_postgres_compatibility import execute as apply_postgres_compatibility
from .fix_erpnext_trends import execute as fix_erpnext_trends

__all__ = [
    'apply_postgres_compatibility',
    'fix_erpnext_trends'
]
