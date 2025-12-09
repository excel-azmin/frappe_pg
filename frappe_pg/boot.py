"""
Boot-time initialization for PostgreSQL compatibility patches.

This module is automatically imported by Frappe during startup to ensure
PostgreSQL compatibility patches are applied as early as possible.
"""

from frappe_pg.patches.postgres_fix import apply_postgres_fixes

# Apply patches immediately when this module is imported
apply_postgres_fixes()

print("frappe_pg: PostgreSQL compatibility module loaded")
