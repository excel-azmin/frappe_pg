"""
Frappe PostgreSQL Compatibility App
===================================

This app provides comprehensive PostgreSQL compatibility for Frappe/ERPNext.

Features:
- Automatic SQL query transformation (MySQL → PostgreSQL)
- Transaction error handling with auto-rollback
- PostgreSQL compatibility functions (GROUP_CONCAT, unix_timestamp, etc.)
- ERPNext trends report GROUP BY fixes

The patches are applied automatically when this module is imported.

Author: Frappe PostgreSQL Team
License: MIT
Repository: https://github.com/excel-azmin/frappe_pg.git
"""

__version__ = "1.0.0"
__author__ = "Frappe PostgreSQL Team"
__license__ = "MIT"

# Import and apply patches immediately when the app loads
try:
    from frappe_pg.postgres.database_patches import apply_postgres_fixes
    apply_postgres_fixes()
except Exception as e:
    # During installation, frappe might not be fully initialized
    print(f"frappe_pg: Will apply database patches later: {e}")

# Apply ERPNext trends.py patch for GROUP BY compatibility
try:
    from frappe_pg.patches.v1.fix_erpnext_trends import apply_trends_patch
    apply_trends_patch()
except Exception as e:
    # ERPNext might not be installed or available yet
    print(f"frappe_pg: Will apply trends patch later: {e}")
